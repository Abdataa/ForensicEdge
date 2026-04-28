"""
backend/app/api/routes_upload.py
-----------------------------------
Forensic image upload and management endpoints.

Endpoints
---------
    POST   /api/v1/images/upload          upload evidence image
    GET    /api/v1/images                 list images
    GET    /api/v1/images/{id}            get single image details
    DELETE /api/v1/images/{id}            delete image
    GET    /api/v1/images/{id}/comparison serve original + enhanced for side-by-side view
"""

import base64
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database     import get_db
from app.core.dependencies import get_current_active_user
from app.models.user       import User
from app.models.forensic_image import ForensicImage, PreprocessedImage
from app.schemas.image_schema import (
    ImageUploadResponse,
    ImageResponse,
    ImageListResponse,
)
from app.services import image_service

router = APIRouter(prefix="/images", tags=["Evidence Images"])


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model = ImageUploadResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Upload a forensic evidence image",
)
async def upload_image(
    request:       Request,
    file:          UploadFile   = File(..., description="Image file (.bmp/.png/.jpg/.jpeg)"),
    evidence_type: str          = Form(..., description="fingerprint | toolmark"),
    db:            AsyncSession = Depends(get_db),
    current_user:  User         = Depends(get_current_active_user),
):
    """
    Upload a fingerprint or toolmark evidence image.
    The image is validated, saved, preprocessed (bilateral + CLAHE + unsharp),
    and embedded by the CNN automatically.
    Poll GET /images/{id} until status='ready' before comparing.
    """
    return await image_service.upload_image(
        file          = file,
        evidence_type = evidence_type,
        user          = current_user,
        db            = db,
        ip_address    = request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
# List
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
    db:            AsyncSession  = Depends(get_db),
    current_user:  User          = Depends(get_current_active_user),
):
    """List images for the current user. Filter by evidence_type if needed."""
    return await image_service.list_images(
        user          = current_user,
        db            = db,
        evidence_type = evidence_type,
        page          = page,
        limit         = limit,
    )


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

@router.get(
    "/{image_id}",
    response_model = ImageResponse,
    summary        = "Get image details and processing status",
)
async def get_image(
    image_id:     int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Return full image metadata including current processing status.
    preprocessed_image and feature_set are populated once processing completes.
    """
    return await image_service.get_image(
        image_id = image_id,
        user     = current_user,
        db       = db,
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{image_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary     = "Delete an uploaded image",
)
async def delete_image(
    image_id:     int,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """Delete an image and its enhanced copy and embedding from disk and database."""
    await image_service.delete_image(
        image_id   = image_id,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
# Image comparison — original vs enhanced
# ---------------------------------------------------------------------------

@router.get(
    "/{image_id}/comparison",
    summary = "Get original vs enhanced image for side-by-side display",
)
async def get_image_comparison(
    image_id:     int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Returns both the original uploaded image and the preprocessed
    (enhanced) version as base64-encoded strings for side-by-side
    display in the frontend dashboard.

    Response shape:
    {
        "image_id":        42,
        "original": {
            "filename":    "finger_1.png",
            "data":        "data:image/png;base64,iVBOR...",
            "size_bytes":  208214,
            "evidence_type": "fingerprint"
        },
        "enhanced": {
            "filename":    "finger_1_enhanced.png",
            "data":        "data:image/png;base64,iVBOR...",
            "processing":  { "bilateral": true, "clahe": true, ... }
        } | null,
        "status": "preprocessed"
    }

    The enhanced field is null when:
        - Preprocessing has not completed yet (status='uploaded' or 'preprocessing')
        - Preprocessing failed

    Raises:
        HTTP 404 — image not found
        HTTP 403 — access denied
        HTTP 404 — original file missing from disk (should not happen in normal flow)
    """
    # Load image with preprocessed_image relationship
    result = await db.execute(
        select(ForensicImage)
        .options(selectinload(ForensicImage.preprocessed_image))
        .where(ForensicImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_id} not found.",
        )
    if image.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    # ── Read original file ────────────────────────────────────────────────
    original_path = Path(image.file_path)
    if not original_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Original file not found on disk: {original_path}. "
                   f"The file may have been moved or deleted.",
        )

    with open(original_path, "rb") as f:
        original_bytes = f.read()

    # Determine MIME type from extension
    ext = original_path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg", ".bmp": "image/bmp"}
    mime = mime_map.get(ext, "image/png")

    original_b64 = f"data:{mime};base64,{base64.b64encode(original_bytes).decode()}"

    # ── Read enhanced file (if available) ─────────────────────────────────
    enhanced_data = None
    preprocessed  = image.preprocessed_image

    if preprocessed and preprocessed.enhanced_path:
        enhanced_path = Path(preprocessed.enhanced_path)
        if enhanced_path.exists():
            with open(enhanced_path, "rb") as f:
                enhanced_bytes = f.read()
            enhanced_b64 = (
                "data:image/png;base64,"
                + base64.b64encode(enhanced_bytes).decode()
            )
            enhanced_data = {
                "filename":   enhanced_path.name,
                "data":       enhanced_b64,
                "processing": preprocessed.processing_steps,
            }

    return {
        "image_id": image.id,
        "original": {
            "filename":     image.original_filename,
            "data":         original_b64,
            "size_bytes":   image.file_size_bytes,
            "evidence_type": image.evidence_type,
        },
        "enhanced": enhanced_data,
        "status":   image.status,
    }