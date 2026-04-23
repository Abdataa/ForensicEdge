"""
backend/app/services/similarity_service.py
--------------------------------------------
Business logic for forensic image similarity comparison.

Toolmark / fingerprint awareness
----------------------------------
This service enforces that only images of the SAME evidence type can be
compared.  Comparing a fingerprint to a toolmark is scientifically invalid
and is rejected with HTTP 400 before reaching the AI engine.

Each evidence type has its own trained model loaded in inference/compare.py.
The correct engine is selected automatically based on evidence_type.

Pipeline
--------
    1. Load both ForensicImage records — validate ownership + status
    2. GUARD: reject cross-type comparison
    3. Load stored feature vectors from FeatureSet table
    4. Run Siamese comparison via inference engine
    5. Save SimilarityResult to DB
    6. Audit log
    7. Return SimilarityResponse
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

import torch

from app.models.forensic_image   import ForensicImage, FeatureSet
from app.models.similarity_result import SimilarityResult
from app.models.user              import User
from app.schemas.similarity_schema import (
    CompareRequest,
    SimilarityResponse,
    SimilarityListResponse,
    ImageSummary,
)
from app.services.log_service import create_log

from ai_engine.inference.compare  import get_engine
from app.services.image_service import _weights_path_for



# ---------------------------------------------------------------------------
async def compare(
    payload:    CompareRequest,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> SimilarityResponse:
    """
    Run forensic similarity comparison between two uploaded images.

    Validates:
        - Both images exist and are accessible by the requesting user
        - Both images have status='ready' (embedding already extracted)
        - Both images are the SAME evidence type (fingerprint vs toolmark guard)

    Uses stored embeddings from the FeatureSet table — the CNN does NOT
    re-run during comparison, making responses fast (~10ms vs ~500ms).

    Raises:
        HTTP 404 — image not found
        HTTP 403 — image belongs to another user (non-admin)
        HTTP 400 — images not yet processed (status != ready)
        HTTP 400 — cross-type comparison attempted
        HTTP 422 — same image compared to itself
    """
    # Validate images are different
    payload.validate_different_images()

    # Load both images
    image_1 = await _get_accessible_image(payload.image_id_1, user, db)
    image_2 = await _get_accessible_image(payload.image_id_2, user, db)

    # Validate both are ready
    for img in (image_1, image_2):
        if img.status != "ready":
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail      = (
                    f"Image {img.id} is not ready for comparison "
                    f"(current status: '{img.status}'). "
                    f"Wait until status becomes 'ready'."
                ),
            )

    # -----------------------------------------------------------------------
    # CROSS-TYPE GUARD — fingerprint vs toolmark comparison is invalid
    # -----------------------------------------------------------------------
    if image_1.evidence_type != image_2.evidence_type:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"Cannot compare images of different evidence types. "
                f"Image {image_1.id} is a '{image_1.evidence_type}' and "
                f"image {image_2.id} is a '{image_2.evidence_type}'. "
                f"Both images must be the same type."
            ),
        )

    evidence_type = image_1.evidence_type   # same for both at this point
    weights = _weights_path_for(evidence_type)

    # Load stored feature vectors from DB
    emb1_tensor = await _load_embedding(image_1.id, db)
    emb2_tensor = await _load_embedding(image_2.id, db)

    # Run comparison using the correct model for this evidence type
    engine = get_engine(weights_path=weights)

    with torch.no_grad():
        similarity = engine._model.similarity_percentage(
            emb1_tensor, emb2_tensor
        ).item()
        cosine     = engine._model.cosine_similarity(
            emb1_tensor, emb2_tensor
        ).item()
        euclidean  = engine._model.euclidean_distance(
            emb1_tensor, emb2_tensor
        ).item()
        match_status = engine._model.match_status(similarity)

    # Save result to DB
    result = SimilarityResult(
        image_id_1             = image_1.id,
        image_id_2             = image_2.id,
        requested_by           = user.id,
        similarity_percentage  = round(similarity, 2),
        cosine_similarity      = round(cosine,     4),
        euclidean_distance     = round(euclidean,  4),
        match_status           = match_status,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)

    # Audit log
    await create_log(
        db          = db,
        action_type = "comparison_completed",
        user_id     = user.id,
        details     = {
            "result_id":     result.id,
            "image_id_1":    image_1.id,
            "image_id_2":    image_2.id,
            "evidence_type": evidence_type,
            "similarity":    result.similarity_percentage,
            "status":        result.match_status,
        },
        ip_address  = ip_address,
    )

    return _build_response(result, image_1, image_2)


# ---------------------------------------------------------------------------
async def get_result(
    result_id: int,
    user:      User,
    db:        AsyncSession,
) -> SimilarityResponse:
    """
    Retrieve a single similarity result by ID.
    Users can access only their own results (admin sees all).

    Raises:
        HTTP 404 — result not found
        HTTP 403 — result belongs to another user (non-admin)
    """
    result_row = await db.execute(
        select(SimilarityResult).where(SimilarityResult.id == result_id)
    )
    result = result_row.scalar_one_or_none()

    if result is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Similarity result {result_id} not found.",
        )
    if result.requested_by != user.id and user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Access denied.",
        )

    image_1 = await _get_image_by_id(result.image_id_1, db)
    image_2 = await _get_image_by_id(result.image_id_2, db)

    return _build_response(result, image_1, image_2)


# ---------------------------------------------------------------------------
async def list_results(
    user:          User,
    db:            AsyncSession,
    evidence_type: Optional[str] = None,
    page:          int           = 1,
    limit:         int           = 20,
) -> SimilarityListResponse:
    """
    List paginated similarity results.
    Supports optional filtering by evidence_type for separate
    fingerprint / toolmark history views on the dashboard.
    """
    limit = min(limit, 100)
    query = (
        select(SimilarityResult)
        .order_by(desc(SimilarityResult.created_at))
    )

    if user.role != "admin":
        query = query.where(SimilarityResult.requested_by == user.id)

    # Filter by evidence type via joined image
    if evidence_type:
        query = (
            query
            .join(ForensicImage, SimilarityResult.image_id_1 == ForensicImage.id)
            .where(ForensicImage.evidence_type == evidence_type)
        )

    count_result = await db.execute(
        query.with_only_columns(SimilarityResult.id)
    )
    total = len(count_result.all())

    offset  = (page - 1) * limit
    rows    = await db.execute(query.offset(offset).limit(limit))
    results = rows.scalars().all()

    responses = []
    for r in results:
        img1 = await _get_image_by_id(r.image_id_1, db)
        img2 = await _get_image_by_id(r.image_id_2, db)
        responses.append(_build_response(r, img1, img2))

    return SimilarityListResponse(
        total   = total,
        page    = page,
        limit   = limit,
        results = responses,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _get_accessible_image(
    image_id: int,
    user:     User,
    db:       AsyncSession,
) -> ForensicImage:
    """Load image and validate user has access."""
    row = await db.execute(
        select(ForensicImage).where(ForensicImage.id == image_id)
    )
    image = row.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Image {image_id} not found.",
        )
    if image.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = f"Access denied to image {image_id}.",
        )
    return image


async def _get_image_by_id(image_id: int, db: AsyncSession) -> ForensicImage:
    """Load image without access check (used internally after ownership is verified)."""
    row = await db.execute(
        select(ForensicImage).where(ForensicImage.id == image_id)
    )
    return row.scalar_one_or_none()


async def _load_embedding(
    image_id: int,
    db:       AsyncSession,
) -> torch.Tensor:
    """
    Load stored feature vector from FeatureSet table and return as tensor.
    Using stored embeddings avoids re-running the CNN on every comparison.
    """
    row = await db.execute(
        select(FeatureSet).where(FeatureSet.image_id == image_id)
    )
    feature_set = row.scalar_one_or_none()

    if feature_set is None:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"No embedding found for image {image_id}. "
                f"Image may not have been fully processed yet."
            ),
        )

    # Reconstruct tensor: list → (1, 256) float32
    import torch
    vector = torch.tensor(
        feature_set.feature_vector,
        dtype=torch.float32,
    ).unsqueeze(0)

    return vector


def _build_response(
    result:  SimilarityResult,
    image_1: ForensicImage,
    image_2: ForensicImage,
) -> SimilarityResponse:
    """Build SimilarityResponse from ORM objects."""
    return SimilarityResponse(
        id                     = result.id,
        similarity_percentage  = result.similarity_percentage,
        cosine_similarity      = result.cosine_similarity,
        euclidean_distance     = result.euclidean_distance,
        match_status           = result.match_status,
        created_at             = result.created_at,
        requested_by           = result.requested_by,
        image_1 = ImageSummary.model_validate(image_1) if image_1 else None,
        image_2 = ImageSummary.model_validate(image_2) if image_2 else None,
    )