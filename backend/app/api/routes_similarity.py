"""
backend/app/api/routes_similarity.py
--------------------------------------
Endpoints for forensic image similarity comparison.

Depends on:
    - app.services.similarity_service (compare, get_result, list_results)
    - app.schemas.similarity_schema (CompareRequest, SimilarityResponse, SimilarityListResponse)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.similarity_schema import (
    CompareRequest,
    SimilarityResponse,
    SimilarityListResponse,
)
from app.services import similarity_service

router = APIRouter(prefix="/compare", tags=["Comparison"])


@router.post(
    "",
    response_model=SimilarityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compare two forensic images",
)
async def compare_images(
    request: Request,
    payload: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Run a similarity comparison between two previously uploaded images.

    Both images must:
    - Belong to the same evidence type (fingerprint or toolmark)
    - Have status = 'ready' (embedding extracted)
    - Be accessible by the current user

    Returns a similarity percentage, match status, and detailed metrics.
    """
    return await similarity_service.compare(
        payload=payload,
        user=current_user,
        db=db,
        ip_address=request.client.host if request.client else None,
    )


@router.get(
    "/results",
    response_model=SimilarityListResponse,
    summary="List comparison history",
)
async def list_comparisons(
    evidence_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve a paginated history of past comparisons.

    - **evidence_type**: filter by 'fingerprint' or 'toolmark'
    - **page**: page number
    - **limit**: items per page
    """
    return await similarity_service.list_results(
        user=current_user,
        db=db,
        evidence_type=evidence_type,
        page=page,
        limit=limit,
    )


@router.get(
    "/results/{result_id}",
    response_model=SimilarityResponse,
    summary="Get a single comparison result",
)
async def get_comparison(
    result_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the full details of a specific comparison result."""
    return await similarity_service.get_result(result_id, current_user, db)