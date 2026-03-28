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
INPUT_DIR  = Path("ai_engine/datasets/processed_clean/train")
OUTPUT_DIR = Path("ai_engine/datasets/augmented/train")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Valid extensions  (SOCOFing uses .BMP — lowercase comparison handles it)
# ---------------------------------------------------------------------------
VALID_EXTS = {".bmp", ".png", ".jpg", ".jpeg"}

# ---------------------------------------------------------------------------
# Augmentation pipeline
#
# Notes:
#   - seed= is NOT passed to A.Compose because it was only added in v2.0.
#     Reproducibility is handled by the global random / numpy seeds above,
#     which work across all albumentations versions.
#   - GaussNoise uses no keyword args so it works on both v1.x (var_limit)
#     and v2.x (std_range).  Default values are fine for fingerprint noise.
#   - All transforms receive a 3-channel (H, W, 3) image — see augment_image.
# ---------------------------------------------------------------------------
transform = A.Compose([
    A.Rotate(limit=10, p=0.7),
    A.GaussNoise(p=0.5),                          # version-safe defaults
    A.RandomBrightnessContrast(p=0.5),
    A.ElasticTransform(alpha=1, sigma=50, p=0.3), # simulates skin deformation
    A.RandomResizedCrop(                           # cropping — per project report
        size=(224, 224),
        height=224, width=224,
        scale=(0.9, 1.0),
        p=0.4
    ),
])


# ---------------------------------------------------------------------------
# augment_image
# ---------------------------------------------------------------------------
def augment_image(img: np.ndarray) -> np.ndarray:
    """
    Apply the augmentation pipeline to a single grayscale image.

    Albumentations expects (H, W, 3) uint8 input for reliable cross-version
    behaviour.  We convert gray → BGR before augmentation and BGR → gray
    after, so the returned image is always (H, W) uint8 grayscale.
    """
    # Defensive dtype cast
    if img.dtype != np.uint8:
        if img.max() <= 1.0:
            img = (img * 255).astype(np.uint8)
        else:
            img = img.astype(np.uint8)

    # Gray (H, W) → BGR (H, W, 3)  — required by albumentations
    img_3ch = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    augmented = transform(image=img_3ch)

    # BGR (H, W, 3) → Gray (H, W)
    result = cv2.cvtColor(augmented["image"], cv2.COLOR_BGR2GRAY)
    return result


# ---------------------------------------------------------------------------
# augment_identity
# ---------------------------------------------------------------------------
def augment_identity(identity_path: Path) -> None:
    """
    For one identity folder:
      - copy the original images to OUTPUT_DIR
      - generate 3 augmented versions of each image
    Result: each identity goes from N images → 4 × N images.
    """
    if not identity_path.is_dir():
        return

    identity_name = identity_path.name

    # Only process recognised image formats (case-insensitive)
    images = [
        f for f in identity_path.iterdir()
        if f.suffix.lower() in VALID_EXTS
    ]

    if not images:
        print(f"WARNING: no valid images in '{identity_name}' — skipping.")
        return

    out_identity = OUTPUT_DIR / identity_name
    out_identity.mkdir(parents=True, exist_ok=True)

    for img_path in images:

        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

        if img is None:
            print(f"WARNING: could not read '{img_path.name}' — skipping.")
            continue

        # 1. Save the original (always as .png for consistency)
        cv2.imwrite(str(out_identity / f"{img_path.stem}.png"), img)

        # 2. Generate 3 augmented versions
        for i in range(3):
            aug_img = augment_image(img)   # always returns (H, W) uint8
            new_name = f"{img_path.stem}_aug{i}.png"
            cv2.imwrite(str(out_identity / new_name), aug_img)


# ---------------------------------------------------------------------------
# run_augmentation
# ---------------------------------------------------------------------------
def run_augmentation() -> None:
    # sorted() gives consistent ordering across OS/filesystems
    identities = sorted(
        p for p in INPUT_DIR.iterdir() if p.is_dir()
    )

    if not identities:
        print(f"ERROR: no identity folders found in {INPUT_DIR}")
        return

    print(f"Starting augmentation for {len(identities)} identities ...")

    for identity in identities:
        augment_identity(identity)

    print("Augmentation finished successfully.")
    print(f"Output written to: {OUTPUT_DIR}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_augmentation()