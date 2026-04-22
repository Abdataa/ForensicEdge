"""
backend/app/services/image_service.py
---------------------------------------
Business logic for forensic evidence image upload and management.

Handles both fingerprint and toolmark evidence types.
Routes each image type to the correct trained model during embedding.

Pipeline per upload
--------------------
    1. Validate file extension + size
    2. Save raw file to storage/uploads/
    3. Create ForensicImage record (status='uploaded')
    4. Run preprocessing pipeline  (status='preprocessing' → 'preprocessed')
    5. Extract CNN embedding        (status='extracting'   → 'ready')
    6. Save PreprocessedImage + FeatureSet records
    7. Log to audit_log

Evidence type routing
----------------------
    Fingerprint → loads fingerprint Siamese model (best_model_fingerprint.pth)
    Toolmark    → loads toolmark    Siamese model (best_model_toolmark.pth)
    Both use the same ForensicInferenceEngine interface from inference/compare.py
"""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
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

# Inference engine — loaded once per evidence type at startup
from ai_engine.inference.compare import get_engine


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".bmp", ".png", ".jpg", ".jpeg"}


def _validate_file(file: UploadFile, file_bytes: bytes) -> None:
    """
    Validate uploaded file extension and size.
    Raises HTTP 400 with a clear message on any violation.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"Invalid file type '{suffix}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = f"File too large. Maximum allowed size is {max_mb} MB.",
        )


def _validate_evidence_type(evidence_type: str) -> None:
    """Reject unsupported evidence types early."""
    allowed = {"fingerprint", "toolmark"}
    if evidence_type not in allowed:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"Invalid evidence_type '{evidence_type}'. "
                f"Must be one of: {', '.join(sorted(allowed))}"
            ),
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
    Upload a forensic evidence image (fingerprint or toolmark).

    Steps:
        1. Read and validate file bytes
        2. Save to storage/uploads/{uuid}{ext}
        3. Create ForensicImage DB record
        4. Trigger async preprocessing + embedding pipeline
        5. Log the upload action

    Args:
        file          : FastAPI UploadFile from the multipart form
        evidence_type : "fingerprint" | "toolmark"
        user          : authenticated user from dependency
        db            : database session
        ip_address    : requester IP for audit log

    Returns:
        ImageUploadResponse with image ID and initial status='uploaded'.
        Frontend should poll GET /images/{id} until status='ready'.
    """
    _validate_evidence_type(evidence_type)

    # Read file bytes
    file_bytes = await file.read()
    _validate_file(file, file_bytes)

    # Save to storage/uploads/ with UUID filename to prevent collisions
    ext       = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_dir  = settings.UPLOAD_DIR / evidence_type
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / unique_name

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # Create DB record
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

    # Audit log
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

    # Trigger preprocessing + embedding in background
    # NOTE: In production this would use FastAPI BackgroundTasks or Celery.
    # For the prototype, we run it inline (image status updates in same request).
    await _preprocess_and_embed(image, file_bytes, db)

    return ImageUploadResponse(
        id                = image.id,
        original_filename = image.original_filename,
        evidence_type     = image.evidence_type,
        file_size_bytes   = image.file_size_bytes,
        status            = image.status,
        upload_date       = image.upload_date,
    )


# ---------------------------------------------------------------------------
# Internal preprocessing + embedding pipeline
# ---------------------------------------------------------------------------

async def _preprocess_and_embed(
    image:      ForensicImage,
    file_bytes: bytes,
    db:         AsyncSession,
) -> None:
    """
    Run the full preprocessing and CNN embedding pipeline on one image.

    Evidence-type routing:
        Fingerprint → fingerprint inference engine (fingerprint model weights)
        Toolmark    → toolmark inference engine    (toolmark model weights)

    Updates image.status at each stage so the frontend progress indicator
    reflects the actual processing state.

    Saves:
        PreprocessedImage record (enhanced_path)
        FeatureSet record        (feature_vector as JSON list)
    """
    try:
        # Stage 1 — preprocessing
        image.status = "preprocessing"
        await db.commit()
        from ai_engine.inference.preprocess import preprocess_from_bytes

        # preprocess_from_bytes applies the same pipeline as enhance.py
        # and returns a (1, 1, 224, 224) float32 tensor
        #_ = preprocess_from_bytes(file_bytes)
        tensor = preprocess_from_bytes(file_bytes)


        # Save preprocessed image to disk
        preprocessed_dir  = settings.UPLOAD_DIR / "preprocessed" / image.evidence_type
        preprocessed_dir.mkdir(parents=True, exist_ok=True)
        enhanced_filename = f"{Path(image.file_path).stem}_enhanced.png"
        enhanced_path     = preprocessed_dir / enhanced_filename

        # Write enhanced image (convert tensor back to uint8 for storage)
        import cv2
        import numpy as np

        # tensor is normalised to [-1,1] — convert back to uint8 for saving
        img_np = ((tensor.squeeze().numpy() + 1.0) / 2.0 * 255).astype(np.uint8)
        cv2.imwrite(str(enhanced_path), img_np)

        preprocessed = PreprocessedImage(
            image_id        = image.id,
            enhanced_path   = str(enhanced_path),
            processing_steps= {
                "resize":      [224, 224],
                "bilateral":   True,
                "clahe":       True,
                "unsharp_mask": True,
                "normalised":  "[-1, 1]",
            },
        )
        db.add(preprocessed)
        image.status = "preprocessed"
        await db.commit()

        # Stage 2 — CNN embedding
        image.status = "extracting"
        await db.commit()

        # Route to correct model based on evidence type
        engine    = get_engine(evidence_type=image.evidence_type)
        embedding = engine.extract_embedding(tensor)
        # embedding is (1, 256) float32 tensor — store as flat JSON list
        vector = embedding.squeeze().tolist()

        feature_set = FeatureSet(
            image_id       = image.id,
            feature_vector = vector,
        )
        db.add(feature_set)
        image.status = "ready"
        await db.commit()

    except Exception as e:
        image.status = "failed"
        await db.commit()
        # Re-raise so the caller can return an appropriate error response
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = f"Processing failed for image {image.id}: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

async def get_image(
    image_id: int,
    user:     User,
    db:       AsyncSession,
) -> ImageResponse:
    """
    Retrieve a single image by ID.
    Users can only access their own images (admin can access all).

    Raises:
        HTTP 404 — image not found
        HTTP 403 — image belongs to a different user (non-admin)
    """
    result = await db.execute(
        select(ForensicImage).where(ForensicImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Image {image_id} not found.",
        )
    if image.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Access denied.",
        )

    return ImageResponse.model_validate(image)


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
    Supports filtering by evidence_type (fingerprint | toolmark).

    Admin users see all images; analysts see only their own.
    """
    limit = min(limit, 100)
    query = select(ForensicImage).order_by(ForensicImage.upload_date.desc())

    # Analysts see only their own images
    if user.role != "admin":
        query = query.where(ForensicImage.user_id == user.id)

    # Optional type filter — supports toolmark/fingerprint separation
    if evidence_type:
        query = query.where(ForensicImage.evidence_type == evidence_type)

    count_result = await db.execute(
        query.with_only_columns(ForensicImage.id)
    )
    total = len(count_result.all())

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
async def delete_image(
    image_id: int,
    user:     User,
    db:       AsyncSession,
    ip_address: Optional[str] = None,
) -> None:
    """
    Delete an image and its associated files from disk and database.
    Cascade delete in DB removes PreprocessedImage and FeatureSet.

    Raises:
        HTTP 404 — image not found
        HTTP 403 — not owner (non-admin)
    """
    result = await db.execute(
        select(ForensicImage).where(ForensicImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Image {image_id} not found.",
        )
    if image.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Access denied.",
        )

    # Remove files from disk
    for path_str in [image.file_path]:
        p = Path(path_str)
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
