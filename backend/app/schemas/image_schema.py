"""
backend/app/schemas/image_schema.py
-------------------------------------
Pydantic schemas for forensic image upload and management.

Note on image upload
--------------------
The actual file bytes are NOT part of these schemas.
FastAPI handles file uploads via UploadFile (multipart/form-data).
These schemas handle the metadata that accompanies or follows the upload.

    POST /api/v1/upload
        Form fields: evidence_type  (validated by ImageUploadMetadata)
        File field:  file           (UploadFile — handled by FastAPI directly)
        Response:    ImageUploadResponse

    GET /api/v1/images/{image_id}
        Response:    ImageResponse  (full details for dashboard display)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.forensic_image import EvidenceType


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ImageUploadMetadata(BaseModel):
    """
    Metadata submitted alongside the file in the upload form.
    The file itself is handled as UploadFile by FastAPI.

    Usage in route:
        @router.post("/upload")
        async def upload(
            file:          UploadFile               = File(...),
            evidence_type: str                      = Form(...),
            db:            AsyncSession             = Depends(get_db),
            user:          User                     = Depends(get_current_active_user),
        ):
    """
    evidence_type: str = Field(
        ...,
        description = "fingerprint | toolmark",
        examples    = ["fingerprint"],
    )

    def validated_evidence_type(self) -> str:
        allowed = {EvidenceType.FINGERPRINT, EvidenceType.TOOLMARK}
        if self.evidence_type not in allowed:
            raise ValueError(
                f"Invalid evidence_type '{self.evidence_type}'. "
                f"Must be one of: {', '.join(allowed)}"
            )
        return self.evidence_type


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class PreprocessedImageResponse(BaseModel):
    """Details of the enhanced version of an image."""
    id:            int
    enhanced_path: str
    created_at:    datetime

    model_config = {"from_attributes": True}


class FeatureSetResponse(BaseModel):
    """Embedding metadata (vector itself excluded — too large for API response)."""
    id:               int
    model_version_id: Optional[int]
    created_at:       datetime

    model_config = {"from_attributes": True}


class ImageUploadResponse(BaseModel):
    """
    Immediate response after a successful image upload.
    Status will be 'uploaded' — processing happens asynchronously.
    The frontend polls GET /images/{id} to check when status becomes 'ready'.
    """
    id:                int
    original_filename: str
    evidence_type:     str
    file_size_bytes:   int
    status:            str
    upload_date:       datetime
    message:           str = "Image uploaded successfully. Processing will begin shortly."

    model_config = {"from_attributes": True}


class ImageResponse(BaseModel):
    """
    Full image details for the dashboard.
    Includes preprocessing and embedding status for progress display.
    """
    id:                int
    original_filename: str
    evidence_type:     str
    file_size_bytes:   int
    status:            str
    upload_date:       datetime
    uploader_id:       int     = Field(alias="user_id")

    # Populated once processing completes
    preprocessed_image: Optional[PreprocessedImageResponse] = None
    feature_set:        Optional[FeatureSetResponse]        = None

    model_config = {
        "from_attributes":  True,
        "populate_by_name": True,   # allow both alias and field name
    }


class ImageListResponse(BaseModel):
    """Paginated list of images for GET /api/v1/images."""
    total:  int
    page:   int
    limit:  int
    images: list[ImageResponse]