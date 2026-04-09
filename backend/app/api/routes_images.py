"""
backend/app/api/routes_images.py
----------------------------------
Endpoints for uploading and managing forensic evidence images.

Depends on:
    - app.services.image_service (upload, list, get, delete)
    - app.schemas.image_schema (ImageUploadResponse, ImageResponse, ImageListResponse)
    - app.api.dependencies (get_current_user)
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.image_schema import (
    ImageUploadResponse,
    ImageResponse,
    ImageListResponse,
)
from app.services import image_service

router = APIRouter(prefix="/images", tags=["Images"])


@router.post(
    "/upload",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a forensic evidence image",
)
async def upload_image(
    request: Request,
    file: UploadFile = File(..., description="Image file (BMP, PNG, JPG, JPEG)"),
    evidence_type: str = Form(
        ..., description="Evidence type: 'fingerprint' or 'toolmark'"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a fingerprint or toolmark image for analysis.

    The image will be processed asynchronously:
    1. Saved to disk
    2. Preprocessed (enhanced)
    3. CNN embedding extracted

    The response returns an image ID; poll `GET /images/{id}` until status becomes 'ready'.
    """
    return await image_service.upload_image(
        file=file,
        evidence_type=evidence_type,
        user=current_user,
        db=db,
        ip_address=request.client.host if request.client else None,
    )


@router.get(
    "",
    response_model=ImageListResponse,
    summary="List uploaded images",
)
async def list_images(
    evidence_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve a paginated list of your uploaded images.

    - **evidence_type**: filter by 'fingerprint' or 'toolmark' (optional)
    - **page**: page number (1-indexed)
    - **limit**: items per page (max 100)
    """
    return await image_service.list_images(
        user=current_user,
        db=db,
        evidence_type=evidence_type,
        page=page,
        limit=limit,
    )


@router.get(
    "/{image_id}",
    response_model=ImageResponse,
    summary="Get image details",
)
async def get_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve full details of a single image, including processing status.
    """
    return await image_service.get_image(image_id, current_user, db)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an image",
)
async def delete_image(
    request: Request,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Permanently delete an image and its associated files and data.
    """
    await image_service.delete_image(
        image_id=image_id,
        user=current_user,
        db=db,
        ip_address=request.client.host if request.client else None,
    )