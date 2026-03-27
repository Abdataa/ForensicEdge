import cv2
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INPUT_DIR  = Path("ai_engine/datasets/processed")
OUTPUT_DIR = Path("ai_engine/datasets/processed_clean")

TARGET_SIZE = (224, 224)

# Valid extensions — SOCOFing uses .BMP; lowercase comparison handles all cases
VALID_EXTS = {".bmp", ".png", ".jpg", ".jpeg"}


# ---------------------------------------------------------------------------
# preprocess_image
# ---------------------------------------------------------------------------
def preprocess_image(img_path: Path):
    """
    Full preprocessing pipeline for a single fingerprint image.

    Steps (in order):
        1. Load as grayscale
        2. Resize to TARGET_SIZE
        3. Bilateral denoise  — removes noise while preserving ridge edges
        4. CLAHE              — local contrast enhancement for ridge clarity
        5. Unsharp masking    — ridge/edge sharpening (per project report)

    Returns:
        uint8 numpy array (H, W) with values in [0, 255], or None on failure.

    NOTE ON NORMALIZATION:
        Pixel normalization (scaling to [0.0, 1.0] and standardization) is
        intentionally NOT applied here.  cv2.imwrite() requires uint8 [0, 255]
        values — saving a float image produces a black file.

        Normalization is handled at training time inside the PyTorch Dataset
        class (siamese_dataset.py) via:
            img = img / 255.0          → scales to [0.0, 1.0]
            torch.from_numpy(img)      → converts to float32 tensor
        This is standard practice in deep learning image pipelines.
    """
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

    if img is None:
        return None

    # 1. Resize
    img = cv2.resize(img, TARGET_SIZE)

    # 2. Bilateral denoise — preserves ridge edges unlike Gaussian blur
    img = cv2.bilateralFilter(img, d=5, sigmaColor=75, sigmaSpace=75)

    # 3. CLAHE — local contrast enhancement
    #    Created inside the function (not globally) so it is thread-safe
    #    if this function is ever called from a multiprocessing pool.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)

    # 4. Ridge/edge enhancement via unsharp masking
    #    Formula: sharpened = 1.5 * original − 0.5 * blurred
    #    This amplifies high-frequency ridge detail suppressed by the
    #    bilateral filter and CLAHE smoothing.
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
    img = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)

    return img   # uint8 [0, 255]


# ---------------------------------------------------------------------------
# process_split
# ---------------------------------------------------------------------------
def process_split(split: str) -> None:
    """
    Preprocess all images in one dataset split (train / val / test).
    Preserves the identity subfolder structure in the output directory.
    Prints a summary showing how many images were processed vs found,
    so any silent data loss is immediately visible.
    """
    input_path  = INPUT_DIR  / split
    output_path = OUTPUT_DIR / split

    if not input_path.exists():
        print(f"Skipping '{split}': folder not found at {input_path}")
        return

    input_count  = 0
    output_count = 0
    failed_files = []

    for img_file in input_path.rglob("*"):

        if not (img_file.is_file() and img_file.suffix.lower() in VALID_EXTS):
            continue

        input_count += 1

        # Preserve identity/image.ext folder structure in output
        relative_path = img_file.relative_to(input_path)
        save_path     = output_path / relative_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        processed_img = preprocess_image(img_file)

        if processed_img is not None:
            cv2.imwrite(str(save_path), processed_img)
            output_count += 1
        else:
            # Log every failure — no silent skips
            failed_files.append(img_file)
            print(f"  WARNING: could not process '{img_file}' — skipping.")

    # Split summary
    print(f"\n--- {split.upper()} SUMMARY ---")
    print(f"  Found:     {input_count}")
    print(f"  Processed: {output_count}")

    if failed_files:
        print(f"  Failed:    {len(failed_files)}")
        print("  Failed files:")
        for f in failed_files:
            print(f"    {f}")
    else:
        print(f"  All images processed successfully.")
    print("-" * 35)


# ---------------------------------------------------------------------------
if __name__ == "__main__":

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for split in ["train", "val", "test"]:
        process_split(split)

    print("\nAll forensic preprocessing finished.")