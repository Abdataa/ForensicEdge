"""
augment_toolmark.py
===================
Data augmentation pipeline for preprocessed tool-mark images.

Analogous to augment.py (fingerprint pipeline), but tuned for breech-face
impression images produced by enhance_toolmark.py.

Key differences from the fingerprint augmentation pipeline:
  - Input is already PNG (uint8) — output of enhance_toolmark.py.
  - Input lives in a flat layout (no train/val/test splits yet):
        ai_engine/datasets/toolmark/processed_clean/<label>/  *.png
  - Breech-face impressions are rotationally symmetric so full 360°
    rotation is valid (fingerprints only use ±10°).
  - Horizontal/vertical flipping is valid — no canonical orientation
    (unlike fingerprints which have arch/loop/whorl direction).
  - Elastic deformation uses a larger alpha (30 vs 1 for fingerprints)
    to capture inter-firing surface variation (pressure, angle, etc.).
  - Brightness/contrast jitter is lighter (±0.1) because CLAHE already
    normalised local contrast during preprocessing.
  - Each original → 5 augmented copies (6× total) because the toolmark
    dataset is smaller (~2,625 scans) than SOCOFing (~6,000).

Output layout (mirrors input — flat, one folder per label):
  ai_engine/datasets/toolmark/augmented/
      firearmA/  *.png  (original + _aug0 … _aug4)
      firearmB/  *.png
      ...

Usage:
  python augment_toolmark.py
"""

import cv2
import numpy as np
import albumentations as A
from pathlib import Path
import random

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Input: flat processed_clean output from enhance_toolmark.py (no splits)
INPUT_DIR  = Path("ai_engine/datasets/toolmark/split/train")

# Output: flat augmented layout (splits are created later during dataset prep)
OUTPUT_DIR = Path("ai_engine/datasets/toolmark/augmented")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VALID_EXTS = {".png", ".bmp", ".jpg", ".jpeg"}

# Each original image → NUM_AUGMENTATIONS additional copies (total: 6× per label)
NUM_AUGMENTATIONS = 5

# ---------------------------------------------------------------------------
# Augmentation pipeline
#
# Design rationale vs fingerprint augment.py:
#   Rotate(limit=45)              — BFI is rotationally symmetric; full ok
#   HorizontalFlip / VerticalFlip  — no canonical handedness; flip = new sample
#   GaussNoise                     — simulates scanner quantisation noise
#                                    (version-safe: no keyword args)
#   RandomBrightnessContrast(0.1)  — light jitter; CLAHE already normalised
#   ElasticTransform(alpha=30)     — inter-firing surface variation
#                                    (fingerprint uses alpha=1)
#   RandomResizedCrop(scale=0.85)  — slightly wider crop range than fingerprint
#
# Version-safety notes:
#   - seed= is NOT passed to A.Compose (only available in albumentations v2.0+).
#     Reproducibility is handled by global numpy/random seeds set above.
#   - GaussNoise uses default keyword args → works on v1.x and v2.x.
# ---------------------------------------------------------------------------
transform = A.Compose([
    A.Rotate(limit=45, p=0.8),
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.5),
    A.GaussNoise(p=0.5),                              # version-safe defaults
    A.RandomBrightnessContrast(
        brightness_limit=0.08,
        contrast_limit=0.08,
        p=0.3,
    ),
    #'''
#
#  Note:-> ElasticTransform can create:
#            - fake microstriations
#            - fake matching patterns
#            - non-physical deformations
#         Metal breech-face impressions do NOT elastically warp like skin.
#         so ElasticTransform is is dangerous for forensic toolmarks.
#         and that is why we removed it
#

   ## A.ElasticTransform(                               # surface deformation
    #    alpha=30,                                     # more aggressive than fingerprint (alpha=1)
    #    sigma=50,
    #    p=0.4,
    #),,
    #''',
    A.RandomResizedCrop(                              # crop — same rationale as fingerprint
        size=(224, 224),
        height=224,
        width=224,
        scale=(0.9, 1.0),                            # slightly wider crop range
        p=0.3,
    ),
])


# ---------------------------------------------------------------------------
# augment_image
# ---------------------------------------------------------------------------
def augment_image(img: np.ndarray) -> np.ndarray:
    """
    Apply the augmentation pipeline to a single grayscale image.

    Albumentations requires (H, W, 3) uint8 input for consistent
    cross-version behaviour.  We convert gray → BGR before augmentation
    and BGR → gray after, exactly as in augment.py for fingerprints.

    Returns (H, W) uint8 grayscale.
    """
    if img.dtype != np.uint8:
        img = (img * 255).astype(np.uint8) if img.max() <= 1.0 else img.astype(np.uint8)

    img_3ch   = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    augmented = transform(image=img_3ch)
    return cv2.cvtColor(augmented["image"], cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------------------
# augment_label
# ---------------------------------------------------------------------------
def augment_label(label_path: Path) -> None:
    """
    For one firearm-label folder:
      1. Copy original images (as PNG) to OUTPUT_DIR/<label>/
      2. Generate NUM_AUGMENTATIONS augmented copies of each image

    Result: N images → (1 + NUM_AUGMENTATIONS) × N = 6N images per label.
    """
    if not label_path.is_dir():
        return

    label = label_path.name

    images = [
        f for f in label_path.iterdir()
        if f.is_file() and f.suffix.lower() in VALID_EXTS
    ]

    if not images:
        print(f"  WARNING: no valid images in '{label}' — skipping.")
        return

    out_dir = OUTPUT_DIR / label
    out_dir.mkdir(parents=True, exist_ok=True)

    for img_path in sorted(images):
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

        if img is None:
            print(f"  WARNING: could not read '{img_path.name}' — skipping.")
            continue

        # 1. Save the original (always as .png for consistency)
        cv2.imwrite(str(out_dir / f"{img_path.stem}.png"), img)

        # 2. Generate NUM_AUGMENTATIONS augmented versions
        for i in range(NUM_AUGMENTATIONS):
            aug_img  = augment_image(img)
            new_name = f"{img_path.stem}_aug{i}.png"
            cv2.imwrite(str(out_dir / new_name), aug_img)


# ---------------------------------------------------------------------------
# run_augmentation
# ---------------------------------------------------------------------------
def run_augmentation() -> None:
    """
    Run augmentation across all firearm-label subfolders in INPUT_DIR.
    Mirrors run_augmentation() in augment.py for fingerprints.
    """
    if not INPUT_DIR.exists():
        print(f"ERROR: input directory not found:\n  {INPUT_DIR}")
        return

    # sorted() gives deterministic ordering across OS/filesystems
    label_dirs = sorted(p for p in INPUT_DIR.iterdir() if p.is_dir())

    if not label_dirs:
        print(f"ERROR: no firearm-label folders found in {INPUT_DIR}")
        return

    print(f"Starting augmentation for {len(label_dirs)} firearm label(s) ...")
    print(f"Each image → {1 + NUM_AUGMENTATIONS}× "
          f"(1 original + {NUM_AUGMENTATIONS} augmented)\n")

    for label_dir in label_dirs:
        augment_label(label_dir)
        print(f"  Done: {label_dir.name}")

    print("\nAugmentation finished successfully.")
    print(f"Output written to: {OUTPUT_DIR}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_augmentation()