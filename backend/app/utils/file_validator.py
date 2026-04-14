"""
backend/app/utils/file_validator.py
-------------------------------------
File validation utilities for forensic evidence uploads.

Why magic bytes matter
----------------------
File extensions can be renamed — a `.exe` renamed to `.png` will pass
an extension-only check.  Magic bytes (the first few bytes of the file
content) reveal the true format regardless of the filename extension.

In a forensic system accepting evidence uploads, validating magic bytes
prevents:
    - Malicious files disguised as images
    - Corrupted images that would crash the preprocessing pipeline
    - Format mismatches that silently produce wrong embeddings

Supported formats
-----------------
    .bmp  — SOCOFing dataset format (Windows Bitmap)
    .png  — Portable Network Graphics
    .jpg  — JPEG
    .jpeg — JPEG

Usage
-----
    from app.utils.file_validator import validate_image_upload

    await validate_image_upload(file, file_bytes)
    # raises HTTPException on any validation failure
"""

from pathlib import Path
from fastapi import HTTPException, UploadFile, status

from app.core.config      import settings
from app.utils.logger     import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Magic byte signatures for allowed image formats
# ---------------------------------------------------------------------------

# Each entry: (format_name, list_of_valid_signatures)
# A signature is a (offset, bytes) tuple — offset into file, expected bytes
MAGIC_BYTES: list[tuple[str, list[tuple[int, bytes]]]] = [
    ("BMP",  [(0, b"BM")]),
    ("PNG",  [(0, b"\x89PNG\r\n\x1a\n")]),
    ("JPEG", [(0, b"\xff\xd8\xff")]),
]


def _check_magic_bytes(file_bytes: bytes) -> bool:
    """
    Return True if file_bytes match any of the allowed image magic signatures.
    """
    for _fmt, signatures in MAGIC_BYTES:
        for offset, magic in signatures:
            end = offset + len(magic)
            if len(file_bytes) >= end and file_bytes[offset:end] == magic:
                return True
    return False


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------

def validate_image_upload(
    file:       UploadFile,
    file_bytes: bytes,
) -> None:
    """
    Validate a forensic image upload.

    Checks (in order):
        1. File must not be empty
        2. Filename must have a recognised extension
        3. File size must not exceed MAX_UPLOAD_SIZE_BYTES
        4. File content must match a recognised image magic signature

    Args:
        file       : FastAPI UploadFile (for filename and content_type)
        file_bytes : already-read bytes from await file.read()

    Raises:
        HTTP 400 with a descriptive message on any validation failure.

    Example:
        file_bytes = await file.read()
        validate_image_upload(file, file_bytes)
        # safe to proceed if no exception raised
    """
    filename = file.filename or ""

    # 1. Empty file
    if not file_bytes:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "Uploaded file is empty.",
        )

    # 2. Extension check
    suffix = Path(filename).suffix.lower()
    allowed = set(settings.ALLOWED_IMAGE_EXTENSIONS)

    if suffix not in allowed:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"File type '{suffix}' is not allowed. "
                f"Accepted formats: {', '.join(sorted(allowed))}"
            ),
        )

    # 3. Size check
    max_bytes = settings.MAX_UPLOAD_SIZE_BYTES
    if len(file_bytes) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"File too large ({len(file_bytes) / 1024 / 1024:.1f} MB). "
                f"Maximum allowed: {max_mb} MB."
            ),
        )

    # 4. Magic bytes check — true format verification
    if not _check_magic_bytes(file_bytes):
        logger.warning(
            "Magic bytes mismatch on upload",
            extra={
                "filename":      filename,
                "extension":     suffix,
                "first_4_bytes": file_bytes[:4].hex(),
            },
        )
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"File content does not match a valid image format. "
                f"The file may be corrupt or its extension may have been renamed. "
                f"Please upload an original, unmodified image file."
            ),
        )

    logger.info(
        "File validation passed",
        extra={
            "filename":   filename,
            "size_bytes": len(file_bytes),
        },
    )


# ---------------------------------------------------------------------------
# Evidence type validator
# ---------------------------------------------------------------------------

VALID_EVIDENCE_TYPES = {"fingerprint", "toolmark"}


def validate_evidence_type(evidence_type: str) -> str:
    """
    Validate and normalise the evidence_type field from an upload form.

    Args:
        evidence_type : string from the multipart form field

    Returns:
        Lowercased, validated evidence_type string.

    Raises:
        HTTP 400 if evidence_type is not "fingerprint" or "toolmark".
    """
    normalised = evidence_type.strip().lower()
    if normalised not in VALID_EVIDENCE_TYPES:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = (
                f"Invalid evidence_type '{evidence_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_EVIDENCE_TYPES))}"
            ),
        )
    return normalised