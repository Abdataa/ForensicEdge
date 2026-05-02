"""
backend/app/services/similarity_service_additions.py
──────────────────────────────────────────────────────
ADD these to your existing similarity_service.py and similarity_schema.py.

Do NOT replace the existing file — just merge these in.
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. ADD TO: backend/app/schemas/similarity_schema.py
# ─────────────────────────────────────────────────────────────────────────────

"""
# In similarity_schema.py — add these two classes:

from pydantic import BaseModel, Field
from typing import List

class DatabaseSearchRequest(BaseModel):
    image_id:  int            = Field(...,  description="ID of the query image (must be ready)")
    top_k:     int            = Field(10,   ge=1, le=50, description="Max candidates to return")
    threshold: float          = Field(0.0,  ge=0, le=100, description="Minimum similarity %")


class SearchCandidate(BaseModel):
    image:                 ImageSummary   # reuse the existing ImageSummary schema
    similarity_percentage: float
    match_status:          str
    cosine_similarity:     float
    euclidean_distance:    float


class DatabaseSearchResponse(BaseModel):
    query_image:    ImageSummary
    total_searched: int
    candidates:     List[SearchCandidate]
"""


# ─────────────────────────────────────────────────────────────────────────────
# 2. ADD TO: backend/app/services/similarity_service.py
# ─────────────────────────────────────────────────────────────────────────────

"""
Paste this function at the bottom of similarity_service.py.

It reuses the existing cosine/euclidean helpers already in the file
and follows the same access-control pattern as compare().
"""

import logging
from typing import Optional

import torch
import torch.nn.functional as F
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forensic_image import ForensicImage, FeatureSet
from app.models.user           import User
from app.schemas.similarity_schema import (
    DatabaseSearchRequest,
    DatabaseSearchResponse,
    SearchCandidate,
    ImageSummary,
)
from app.services.log_service import create_log

logger = logging.getLogger(__name__)

# Thresholds — must match those in compare() for consistency
MATCH_THRESHOLD          = 80.0   # % → MATCH
POSSIBLE_MATCH_THRESHOLD = 60.0   # % → POSSIBLE MATCH


def _pct_to_status(pct: float) -> str:
    if pct >= MATCH_THRESHOLD:
        return "MATCH"
    if pct >= POSSIBLE_MATCH_THRESHOLD:
        return "POSSIBLE MATCH"
    return "NO MATCH"


async def search_database(
    payload:    DatabaseSearchRequest,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> DatabaseSearchResponse:
    """
    Rank all stored images of the same evidence type by similarity
    to the query image and return the top-k candidates.

    Steps
    -----
    1. Load the query image + its FeatureSet (must be 'ready').
    2. Load all OTHER images of the same evidence type that have a FeatureSet.
    3. Compute cosine similarity + euclidean distance for each candidate.
    4. Filter by threshold, sort descending, return top_k.
    5. Write an audit log entry.
    """
    # ── 1. Load query image ──────────────────────────────────────────────────
    q_result = await db.execute(
        select(ForensicImage)
        .options(selectinload(ForensicImage.feature_set))
        .where(ForensicImage.id == payload.image_id)
    )
    query_img = q_result.scalar_one_or_none()

    if query_img is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {payload.image_id} not found.",
        )
    if query_img.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )
    if query_img.status != "ready" or query_img.feature_set is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Image {payload.image_id} is not ready for comparison "
                f"(status={query_img.status}). "
                "Wait for embedding extraction to complete."
            ),
        )

    query_vector = torch.tensor(query_img.feature_set.feature_vector, dtype=torch.float32)

    # ── 2. Load all candidate images of the same evidence type ───────────────
    # Admins search across all users; regular users only search their own images.
    cand_query = (
        select(ForensicImage)
        .options(selectinload(ForensicImage.feature_set))
        .where(
            ForensicImage.evidence_type == query_img.evidence_type,
            ForensicImage.status        == "ready",
            ForensicImage.id            != payload.image_id,   # exclude self
        )
    )
    if user.role != "admin":
        cand_query = cand_query.where(ForensicImage.user_id == user.id)

    cand_result = await db.execute(cand_query)
    candidates  = [img for img in cand_result.scalars().all() if img.feature_set is not None]

    total_searched = len(candidates)
    logger.info(
        f"Database search: query_image={payload.image_id}, "
        f"evidence_type={query_img.evidence_type}, candidates={total_searched}"
    )

    # ── 3. Score each candidate ───────────────────────────────────────────────
    scored: list[tuple[float, float, float, ForensicImage]] = []

    for cand in candidates:
        cand_vector = torch.tensor(cand.feature_set.feature_vector, dtype=torch.float32)

        # Cosine similarity — clamp to [-1, 1] to guard floating-point drift
        cosine = float(
            F.cosine_similarity(query_vector.unsqueeze(0), cand_vector.unsqueeze(0))
            .clamp(-1.0, 1.0)
            .item()
        )

        # Euclidean distance in normalised embedding space
        euclidean = float(torch.dist(query_vector, cand_vector).item())

        # Convert cosine similarity → 0–100 % (same formula as compare())
        pct = round((cosine + 1.0) / 2.0 * 100.0, 2)

        scored.append((pct, cosine, euclidean, cand))

    # ── 4. Filter by threshold, sort, limit ──────────────────────────────────
    filtered = [s for s in scored if s[0] >= payload.threshold]
    filtered.sort(key=lambda x: x[0], reverse=True)
    top      = filtered[: payload.top_k]

    result_candidates = [
        SearchCandidate(
            image = ImageSummary(
                id                = img.id,
                original_filename = img.original_filename,
                evidence_type     = img.evidence_type,
                status            = img.status,
            ),
            similarity_percentage = pct,
            match_status          = _pct_to_status(pct),
            cosine_similarity     = cosine,
            euclidean_distance    = euclidean,
        )
        for pct, cosine, euclidean, img in top
    ]

    # ── 5. Audit log ──────────────────────────────────────────────────────────
    await create_log(
        db          = db,
        action_type = "database_search",
        user_id     = user.id,
        details     = {
            "query_image_id": payload.image_id,
            "evidence_type":  query_img.evidence_type,
            "total_searched": total_searched,
            "top_k":          payload.top_k,
            "threshold":      payload.threshold,
            "matches_found":  len(result_candidates),
        },
        ip_address  = ip_address,
    )

    return DatabaseSearchResponse(
        query_image = ImageSummary(
            id                = query_img.id,
            original_filename = query_img.original_filename,
            evidence_type     = query_img.evidence_type,
            status            = query_img.status,
        ),
        total_searched = total_searched,
        candidates     = result_candidates,
    )