"""
ai_engine/inference/preprocess.py
----------------------------------
Single-image preprocessing for inference time.

Mirrors the exact pipeline used in enhance.py during training:
    1. Decode raw bytes  OR  read from file path
    2. Grayscale conversion
    3. Resize to 224 × 224
    4. Bilateral denoise   (preserves ridge edges)
    5. CLAHE               (local contrast enhancement)
    6. Unsharp masking     (ridge/edge sharpening)
    7. Normalise to float32 tensor [-1.0, 1.0]  (1, H, W)

Keeping inference preprocessing IDENTICAL to training preprocessing is
critical.  Any mismatch (e.g. skipping CLAHE at inference) shifts the
embedding distribution and degrades similarity scores.

Used by
-------
    ai_engine/inference/feature_extractor.py
    ai_engine/inference/compare.py
    backend/app/services/image_service.py  (via feature_extractor)
"""

import cv2
import numpy as np
import torch
from pathlib import Path


# Must match enhance.py TARGET_SIZE exactly
TARGET_SIZE = (224, 224)


def preprocess_from_path(img_path: str | Path) -> torch.Tensor:
    """
    Load an image from disk and return a normalised float32 tensor.

    Args:
        img_path : path to a .bmp / .png / .jpg / .jpeg file.

    Returns:
        float32 tensor  (1, 1, 224, 224)  — batch dim included,
        values in [−1.0, 1.0], ready to pass directly to the model.

    Raises:
        FileNotFoundError : if the path does not exist.
        ValueError        : if cv2 cannot decode the file.
    """
    img_path = Path(img_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {img_path}")

    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(
            f"cv2 could not decode '{img_path}'. "
            f"File may be corrupt or an unsupported format."
        )

    return _pipeline(img)


def preprocess_from_bytes(raw_bytes: bytes) -> torch.Tensor:
    """
    Decode raw image bytes (from a FastAPI UploadFile) and return a
    normalised float32 tensor.

    Args:
        raw_bytes : raw image bytes (e.g. from await file.read()).

    Returns:
        float32 tensor  (1, 1, 224, 224), values in [−1.0, 1.0].

    Raises:
        ValueError : if the bytes cannot be decoded as an image.
    """
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(
            "Could not decode image from bytes. "
            "Ensure the upload is a valid image file (.bmp/.png/.jpg/.jpeg)."
        )

    return _pipeline(img)


# ---------------------------------------------------------------------------
# Internal pipeline — mirrors enhance.py exactly
# ---------------------------------------------------------------------------
def _pipeline(img: np.ndarray) -> torch.Tensor:
    """
    Apply the full preprocessing pipeline to a grayscale uint8 array.

    Steps (identical to enhance.py):
        1. Resize to TARGET_SIZE
        2. Bilateral denoise
        3. CLAHE  (created inside function — thread-safe)
        4. Unsharp masking (ridge sharpening)
        5. Scale [0, 255] → [0.0, 1.0]
        6. Standardise [0.0, 1.0] → [−1.0, 1.0]
        7. Convert to float32 tensor and add batch + channel dims → (1, 1, H, W)

    Returns:
        float32 tensor  (1, 1, 224, 224)
    """
    # 1. Resize
    img = cv2.resize(img, TARGET_SIZE)

    # 2. Bilateral denoise — preserves ridge edges
    img = cv2.bilateralFilter(img, d=5, sigmaColor=75, sigmaSpace=75)

    # 3. CLAHE — local contrast enhancement (thread-safe: created per call)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img   = clahe.apply(img)

    # 4. Unsharp masking — ridge/edge sharpening
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
    img     = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)

    # 5. Scale to [0.0, 1.0]
    img = img.astype("float32") / 255.0

    # 6. Standardise to [−1.0, 1.0]  (matches siamese_dataset.py)
    img = (img - 0.5) / 0.5

    # 7. Tensor: (H, W) → (1, 1, H, W)  [batch=1, channels=1]
    tensor = torch.from_numpy(img).unsqueeze(0).unsqueeze(0)

    return tensor   # float32, (1, 1, 224, 224)