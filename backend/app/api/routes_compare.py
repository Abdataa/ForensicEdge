"""
backend/app/api/routes_compare.py
-----------------------------------
Forensic similarity comparison endpoints.

Endpoints
---------
    POST /api/v1/compare              — run similarity analysis on two images
    GET  /api/v1/compare              — list past comparison results
    GET  /api/v1/compare/{result_id}  — get single result

Toolmark / fingerprint awareness
---------------------------------
Comparing a fingerprint to a toolmark is rejected with HTTP 400.
The correct model (fingerprint or toolmark) is selected automatically
by similarity_service.py based on the evidence_type of the images.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database     import get_db
from app.core.dependencies import CurrentUser
from app.schemas.similarity_schema import (
    CompareRequest,
    SimilarityResponse,
    SimilarityListResponse,
)
from app.services import similarity_service

router = APIRouter(prefix="/compare", tags=["Similarity Analysis"])


# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model = SimilarityResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Compare two forensic images",
)
async def compare_images(
    payload:      CompareRequest,
    request:      Request,
    current_user: CurrentUser  ,
    db:           AsyncSession = Depends(get_db),
):
    """
    Run forensic similarity analysis between two uploaded images.

    Both images must:
    - Belong to the current user (or user is admin)
    - Have status = `ready` (embedding extracted)
    - Be the **same evidence type** (fingerprint vs toolmark comparison is invalid)

    Returns similarity metrics:
    - **similarity_percentage**: 0–100% investigator-friendly score
    - **match_status**: MATCH | POSSIBLE MATCH | NO MATCH
    - **cosine_similarity**: raw embedding similarity [-1, 1]
    - **euclidean_distance**: L2 distance between embeddings [0, 2]

    The result is stored and can be retrieved later via `GET /compare/{id}`.
    """
    return await similarity_service.compare(
        payload    = payload,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model = SimilarityListResponse,
    summary        = "List past comparison results",
)
async def list_results(
    current_user:  CurrentUser   ,
    evidence_type: Optional[str] = None,
    page:          int           = 1,
    limit:         int           = 20,

    db:            AsyncSession  = Depends(get_db),
):
    """
    List all similarity comparison results for the current user.

    - **evidence_type**: filter by `fingerprint` or `toolmark` (optional)
    - Supports pagination via **page** and **limit**
    - Admins see all users' results
    """
    return await similarity_service.list_results(
        user          = current_user,
        db            = db,
        evidence_type = evidence_type,
        page          = page,
        limit         = limit,
    )


# ---------------------------------------------------------------------------
@router.get(
    "/{result_id}",
    response_model = SimilarityResponse,
    summary        = "Get a single comparison result",
)
async def get_result(
    result_id:    int,
    current_user: CurrentUser  ,
    db:           AsyncSession = Depends(get_db),
):
    """
    Retrieve a single forensic similarity result by ID.
    Includes image summaries for both compared images.
    """
    return await similarity_service.get_result(
        result_id = result_id,
        user      = current_user,
        db        = db,
    )