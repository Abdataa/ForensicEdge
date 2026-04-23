"""
backend/app/services/image_service.py
---------------------------------------
Business logic for forensic evidence image upload and management.

Async SQLAlchemy relationship loading
---------------------------------------
ForensicImage has two relationships used by ImageResponse:
    - preprocessed_image  (one-to-one with PreprocessedImage)
    - feature_set         (one-to-one with FeatureSet)

In async SQLAlchemy, lazy loading (the default) is DISABLED.
When Pydantic calls model_validate(image) it reads these attributes,
which triggers a SQL SELECT. Without an active async session at that
point the driver raises:
    MissingGreenlet: greenlet_spawn has not been called

Fix: every query that returns a ForensicImage destined for ImageResponse
must eagerly load both relationships using selectinload():

    select(ForensicImage)
        .options(
            selectinload(ForensicImage.preprocessed_image),
            selectinload(ForensicImage.feature_set),
        )

This issues two extra SELECTs (one per relationship) alongside the
main query and populates the attributes before the session closes.
Pydantic can then read them without triggering any further IO.

Model weights / graceful degradation
---------------------------------------
If best_model.pth has not been trained yet the pipeline completes
preprocessing and leaves status='preprocessed' instead of failing.
Once weights are placed at the resolved path, re-uploading will
run the full pipeline to status='ready' automatically.
"""

import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config  import settings
from app.models.forensic_image import (
    ForensicImage,
    PreprocessedImage,
    FeatureSet,
)
from app.models.user  import User
from app.schemas.image_schema import (
    ImageUploadResponse,
    ImageResponse,
    ImageListResponse,
)
from app.services.log_service import create_log

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared eager-load options
# ---------------------------------------------------------------------------
# Reused in every query that returns ImageResponse so we never forget one.
_IMAGE_LOAD_OPTIONS = [
    selectinload(ForensicImage.preprocessed_image),
    selectinload(ForensicImage.feature_set),
]

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".bmp", ".png", ".jpg", ".jpeg"}


def _validate_file(file: UploadFile, file_bytes: bytes) -> None:
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file type '{suffix}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum allowed size is {max_mb} MB.",
        )


def _validate_evidence_type(evidence_type: str) -> None:
    allowed = {"fingerprint", "toolmark"}
    if evidence_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid evidence_type '{evidence_type}'. "
                f"Must be one of: {', '.join(sorted(allowed))}"
            ),
        )


# ---------------------------------------------------------------------------
# Model weights path resolver
# ---------------------------------------------------------------------------

def _weights_path_for(evidence_type: str) -> Path:
    """
    Resolve the model weights path for the given evidence type.

    Uses __file__ to find the project root so the path is correct
    regardless of the working directory uvicorn was launched from.

    Priority:
        1. settings.MODEL_WEIGHTS_PATH_FINGERPRINT / _TOOLMARK (.env)
        2. <project_root>/ai_engine/models/weights/{type}/best_model.pth
    """
    # backend/app/services/image_service.py → 3 levels up = backend/
    # one more level up = project root
    project_root = Path(__file__).resolve().parents[3]

    attr = (
        "MODEL_WEIGHTS_PATH_FINGERPRINT"
        if evidence_type == "fingerprint"
        else "MODEL_WEIGHTS_PATH_TOOLMARK"
    )
    raw = getattr(settings, attr, None)

    if raw:
        p = Path(raw)
        return p if p.is_absolute() else project_root / p

    return (
        project_root
        / "ai_engine" / "models" / "weights"
        / evidence_type / "best_model.pth"
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

async def upload_image(
    file:          UploadFile,
    evidence_type: str,
    user:          User,
    db:            AsyncSession,
    ip_address:    Optional[str] = None,
) -> ImageUploadResponse:
    """
    Upload a forensic evidence image.
    Validates, saves, preprocesses, and attempts CNN embedding.
    If model weights are not yet available, image stays 'preprocessed'.
    Returns ImageUploadResponse (flat — no relationships to load).
    """
    _validate_evidence_type(evidence_type)
    file_bytes = await file.read()
    _validate_file(file, file_bytes)

    ext         = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_dir    = settings.UPLOAD_DIR / evidence_type
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path   = save_dir / unique_name

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    image = ForensicImage(
        user_id           = user.id,
        original_filename = file.filename,
        file_path         = str(save_path),
        file_size_bytes   = len(file_bytes),
        evidence_type     = evidence_type,
        status            = "uploaded",
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    await create_log(
        db          = db,
        action_type = "image_uploaded",
        user_id     = user.id,
        details     = {
            "image_id":      image.id,
            "evidence_type": evidence_type,
            "filename":      file.filename,
            "size_bytes":    len(file_bytes),
        },
        ip_address  = ip_address,
    )

    await _preprocess_and_embed(image, file_bytes, db)

    # ImageUploadResponse is flat — no relationship fields — safe to build directly
    return ImageUploadResponse(
        id                = image.id,
        original_filename = image.original_filename,
        evidence_type     = image.evidence_type,
        file_size_bytes   = image.file_size_bytes,
        status            = image.status,
        upload_date       = image.upload_date,
    )


# ---------------------------------------------------------------------------
# Preprocessing + embedding pipeline
# ---------------------------------------------------------------------------

async def _preprocess_and_embed(
    image:      ForensicImage,
    file_bytes: bytes,
    db:         AsyncSession,
) -> None:
    """
    Stage 1 — Preprocessing (always runs):
        Applies bilateral filter, CLAHE, unsharp masking.
        Saves enhanced image to disk.
        Sets status='preprocessed'.

    Stage 2 — CNN Embedding (only if weights exist):
        Passes file_bytes (not tensor) to extract_embedding().
        Sets status='ready' on success.
        If weights missing → leaves status='preprocessed', NOT 'failed'.
    """
    try:
        # ── Stage 1: Preprocessing ─────────────────────────────────────
        image.status = "preprocessing"
        await db.commit()

        import cv2
        import numpy as np
        from ai_engine.inference.preprocess import preprocess_from_bytes

        tensor = preprocess_from_bytes(file_bytes)

        # Convert tensor [-1, 1] → uint8 [0, 255] for disk storage
        img_np = ((tensor.squeeze().numpy() + 1.0) / 2.0 * 255).astype(np.uint8)

        preprocessed_dir  = settings.UPLOAD_DIR / "preprocessed" / image.evidence_type
        preprocessed_dir.mkdir(parents=True, exist_ok=True)
        enhanced_path     = preprocessed_dir / f"{Path(image.file_path).stem}_enhanced.png"
        cv2.imwrite(str(enhanced_path), img_np)

        db.add(PreprocessedImage(
            image_id         = image.id,
            enhanced_path    = str(enhanced_path),
            processing_steps = {
                "resize":       [224, 224],
                "bilateral":    True,
                "clahe":        True,
                "unsharp_mask": True,
                "normalised":   "[-1, 1]",
            },
        ))
        image.status = "preprocessed"
        await db.commit()
        logger.info(f"Image {image.id}: preprocessing complete")

        # ── Stage 2: CNN Embedding ──────────────────────────────────────
        weights = _weights_path_for(image.evidence_type)

        if not weights.exists():
            logger.warning(
                f"Image {image.id}: model weights not found at {weights}. "
                f"Status stays 'preprocessed'. Train the model and re-upload."
            )
            return  # leave status='preprocessed' — NOT 'failed'

        image.status = "extracting"
        await db.commit()

        from ai_engine.inference.compare import get_engine

        engine    = get_engine(weights_path=weights)
        embedding = engine.extract_embedding(file_bytes)   # bytes, not tensor
        vector    = embedding.squeeze().tolist()

        db.add(FeatureSet(image_id=image.id, feature_vector=vector))
        image.status = "ready"
        await db.commit()
        logger.info(f"Image {image.id}: embedding complete (dim={len(vector)})")

    except HTTPException:
        image.status = "failed"
        await db.commit()
        raise

    except Exception as e:
        image.status = "failed"
        await db.commit()
        logger.error(f"Image {image.id}: pipeline error — {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed for image {image.id}: {str(e)}",
        )


# ---------------------------------------------------------------------------
# get_image  — eager loads both relationships
# ---------------------------------------------------------------------------

async def get_image(
    image_id: int,
    user:     User,
    db:       AsyncSession,
) -> ImageResponse:
    """
    Retrieve a single image by ID.

    Uses selectinload() for preprocessed_image and feature_set so
    Pydantic can read them without triggering lazy IO (MissingGreenlet).
    """
    result = await db.execute(
        select(ForensicImage)
        .options(*_IMAGE_LOAD_OPTIONS)          # ← eager load relationships
        .where(ForensicImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_id} not found.",
        )
    if image.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    return ImageResponse.model_validate(image)


# ---------------------------------------------------------------------------
# list_images  — eager loads both relationships for every row
# ---------------------------------------------------------------------------

async def list_images(
    user:          User,
    db:            AsyncSession,
    evidence_type: Optional[str] = None,
    page:          int           = 1,
    limit:         int           = 20,
) -> ImageListResponse:
    """
    List forensic images for the current user.

    selectinload() issues two additional SELECTs (one per relationship)
    to populate preprocessed_image and feature_set for all rows in one
    round-trip, preventing N+1 queries and the MissingGreenlet error.
    """
    limit = min(limit, 100)

    query = (
        select(ForensicImage)
        .options(*_IMAGE_LOAD_OPTIONS)          # ← eager load relationships
        .order_by(ForensicImage.upload_date.desc())
    )

    if user.role != "admin":
        query = query.where(ForensicImage.user_id == user.id)
    if evidence_type:
        query = query.where(ForensicImage.evidence_type == evidence_type)

    # Count total (without loading relationships — faster)
    count_query  = select(ForensicImage.id)
    if user.role != "admin":
        count_query = count_query.where(ForensicImage.user_id == user.id)
    if evidence_type:
        count_query = count_query.where(ForensicImage.evidence_type == evidence_type)

    count_result = await db.execute(count_query)
    total        = len(count_result.all())

    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    images = result.scalars().all()

    return ImageListResponse(
        total  = total,
        page   = page,
        limit  = limit,
        images = [ImageResponse.model_validate(img) for img in images],
    )


# ---------------------------------------------------------------------------
# delete_image
# ---------------------------------------------------------------------------

async def delete_image(
    image_id:   int,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> None:
    """
    Delete an image and its associated files from disk and database.
    No relationship loading needed here — we only need id, user_id, file_path.
    """
    result = await db.execute(
        select(ForensicImage).where(ForensicImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_id} not found.",
        )
    if image.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    p = Path(image.file_path)
    if p.exists():
        p.unlink()

    await db.delete(image)
    await db.commit()

    await create_log(
        db          = db,
        action_type = "image_deleted",
        user_id     = user.id,
        details     = {"image_id": image_id},
        ip_address  = ip_address,
    )