"""
backend/app/api/routes_upload.py
----------------------------------
Forensic image upload and management endpoints.

Endpoints
---------
    POST   /api/v1/images/upload          — upload evidence image
    GET    /api/v1/images                 — list images (filter by type)
    GET    /api/v1/images/{image_id}      — get single image details
    DELETE /api/v1/images/{image_id}      — delete image

Evidence type support
---------------------
    evidence_type=fingerprint  → stored in uploads/fingerprint/
                                  processed by fingerprint model
    evidence_type=toolmark     → stored in uploads/toolmark/
                                  processed by toolmark model

Both types go through the same upload endpoint — the evidence_type
form field determines routing.
"""

from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form,
    Request, UploadFile, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database     import get_db
from app.core.dependencies import CurrentUser
from app.schemas.image_schema import (
    ImageUploadResponse,
    ImageResponse,
    ImageListResponse,
)
from app.services import image_service

router = APIRouter(prefix="/images", tags=["Evidence Images"])


# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model = ImageUploadResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Upload a forensic evidence image",
)
async def upload_image(
    request:       Request,
    file:          UploadFile       = File(..., description="Image file (.bmp/.png/.jpg/.jpeg)"),
    evidence_type: str              = Form(..., description="fingerprint | toolmark"),
    current_user:  CurrentUser      = Depends(),
    db:            AsyncSession     = Depends(get_db),
):
    """
    Upload a fingerprint or toolmark evidence image for analysis.

    The image is immediately:
    1. Validated (format + size)
    2. Saved to storage/uploads/{evidence_type}/
    3. Preprocessed (denoise → CLAHE → ridge enhance)
    4. Embedded via the appropriate CNN model
    5. Stored as ready for comparison

    Poll `GET /images/{id}` to track processing status.
    Status will be `ready` when the image is available for comparison.
    """
    return await image_service.upload_image(
        file          = file,
        evidence_type = evidence_type,
        user          = current_user,
        db            = db,
        ip_address    = request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model = ImageListResponse,
    summary        = "List uploaded images",
)
async def list_images(
    evidence_type: Optional[str] = None,
    page:          int           = 1,
    limit:         int           = 20,
    current_user:  CurrentUser   = Depends(),
    db:            AsyncSession  = Depends(get_db),
):
    """
    List forensic images uploaded by the current user.

    - **evidence_type**: filter by `fingerprint` or `toolmark` (optional)
    - **page** / **limit**: pagination controls
    - Admins see all users' images; analysts see only their own
    """
    return await image_service.list_images(
        user          = current_user,
        db            = db,
        evidence_type = evidence_type,
        page          = page,
        limit         = limit,
    )


# ---------------------------------------------------------------------------
@router.get(
    "/{image_id}",
    response_model = ImageResponse,
    summary        = "Get image details and processing status",
)
async def get_image(
    image_id:     int,
    current_user: CurrentUser  = Depends(),
    db:           AsyncSession = Depends(get_db),
):
    """
    Retrieve details for a single image including its processing status.

    Status values:
    - `uploaded`      — file received, processing not started
    - `preprocessing` — OpenCV pipeline running
    - `preprocessed`  — enhanced image saved
    - `extracting`    — CNN embedding being computed
    - `ready`         — embedding stored, image available for comparison
    - `failed`        — processing error, re-upload recommended
    """
    return await image_service.get_image(
        image_id = image_id,
        user     = current_user,
        db       = db,
    )


# ---------------------------------------------------------------------------
@router.delete(
    "/{image_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary     = "Delete an uploaded image",
)
async def delete_image(
    image_id:     int,
    request:      Request,
    current_user: CurrentUser  = Depends(),
    db:           AsyncSession = Depends(get_db),
):
    """
    Delete a forensic image and its associated files from disk and database.
    Cascade deletes the preprocessed image and feature embedding records.
    """
    await image_service.delete_image(
        image_id   = image_id,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )