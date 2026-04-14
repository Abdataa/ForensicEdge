"""
backend/app/utils/image_processing.py
---------------------------------------
OpenCV / PIL image processing helpers for the ForensicEdge backend.

These utilities are used by image_service.py to prepare images for
display in the React dashboard — resizing thumbnails, converting between
formats, and reading image dimensions.

Note: The forensic preprocessing pipeline (CLAHE, bilateral filter,
unsharp masking) lives in ai_engine/inference/preprocess.py, NOT here.
These helpers are only for backend image handling tasks.
"""

import io
from pathlib import Path
from typing  import Optional, Tuple

import cv2
import numpy as np
from fastapi import HTTPException, status

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Image reading
# ---------------------------------------------------------------------------

def read_image_from_bytes(file_bytes: bytes) -> np.ndarray:
    """
    Decode raw image bytes to a numpy array using OpenCV.

    Args:
        file_bytes : raw bytes from file.read()

    Returns:
        BGR numpy array  (H, W, 3)  or grayscale  (H, W)

    Raises:
        HTTP 400 if bytes cannot be decoded as an image.
    """
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)

    if img is None:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "Could not decode image. File may be corrupt.",
        )
    return img


def read_image_from_path(path: str | Path) -> np.ndarray:
    """
    Read an image from disk using OpenCV.

    Raises:
        HTTP 404 if file does not exist.
        HTTP 400 if file cannot be decoded.
    """
    path = Path(path)
    if not path.exists():
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Image file not found: {path}",
        )

    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = f"Could not read image: {path}",
        )
    return img


# ---------------------------------------------------------------------------
# Image metadata
# ---------------------------------------------------------------------------

def get_image_dimensions(file_bytes: bytes) -> Tuple[int, int]:
    """
    Return (width, height) of an image from its bytes.
    Used to display image dimensions in the dashboard.
    """
    img = read_image_from_bytes(file_bytes)
    h, w = img.shape[:2]
    return w, h


def get_image_dimensions_from_path(path: str | Path) -> Tuple[int, int]:
    """Return (width, height) of an image from its file path."""
    img = read_image_from_path(path)
    h, w = img.shape[:2]
    return w, h


# ---------------------------------------------------------------------------
# Thumbnail generation
# ---------------------------------------------------------------------------

def generate_thumbnail(
    file_bytes:   bytes,
    max_width:    int = 300,
    max_height:   int = 300,
    output_format: str = "PNG",
) -> bytes:
    """
    Generate a thumbnail from image bytes.

    Used by the React dashboard to display preview images without
    serving full-resolution forensic images over the network.

    Args:
        file_bytes    : raw image bytes
        max_width     : maximum thumbnail width in pixels
        max_height    : maximum thumbnail height in pixels
        output_format : "PNG" (default) or "JPEG"

    Returns:
        Thumbnail as raw bytes in the specified format.
    """
    img  = read_image_from_bytes(file_bytes)
    h, w = img.shape[:2]

    # Calculate scale to fit within max dimensions while preserving aspect ratio
    scale = min(max_width / w, max_height / h, 1.0)

    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img   = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Encode to target format
    ext    = ".png" if output_format.upper() == "PNG" else ".jpg"
    _, buf = cv2.imencode(ext, img)

    logger.info(
        "Thumbnail generated",
        extra={
            "original_size": f"{w}x{h}",
            "thumbnail_size": f"{img.shape[1]}x{img.shape[0]}",
        },
    )
    return buf.tobytes()


def generate_thumbnail_from_path(
    path:          str | Path,
    max_width:     int = 300,
    max_height:    int = 300,
    output_format: str = "PNG",
) -> bytes:
    """Generate a thumbnail from an image file path."""
    path = Path(path)
    with open(path, "rb") as f:
        file_bytes = f.read()
    return generate_thumbnail(file_bytes, max_width, max_height, output_format)


# ---------------------------------------------------------------------------
# Format conversion
# ---------------------------------------------------------------------------

def convert_to_png(file_bytes: bytes) -> bytes:
    """
    Convert any supported image format to PNG bytes.

    Used to normalise BMP uploads (SOCOFing format) before
    storing enhanced copies — PNG is smaller and web-friendly.
    """
    img    = read_image_from_bytes(file_bytes)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def bytes_to_base64(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Convert image bytes to a base64 data URI for the React dashboard.

    Returns a string like:
        "data:image/png;base64,iVBORw0KGgo..."

    Used when serving image previews inline in API responses rather
    than via separate file endpoints.
    """
    import base64
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"