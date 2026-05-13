"""
split_toolmark_dataset.py
=========================

Create train / val / test splits for preprocessed toolmark PNG images.

This script is run AFTER:
    enhance_toolmark.py

and BEFORE:
    augment_toolmark.py

Input layout (flat):
    ai_engine/datasets/toolmark/processed_clean/
        firearmA/*.png
        firearmB/*.png
        ...

Output layout:
    ai_engine/datasets/toolmark/split/
        train/
            firearmA/*.png
            firearmB/*.png
            ...
        val/
            firearmA/*.png
            firearmB/*.png
            ...
        test/
            firearmA/*.png
            firearmB/*.png
            ...

Why split BEFORE augmentation?
------------------------------
Validation and test sets must contain ONLY real, untouched images.

If augmentation is performed before splitting, augmented versions of the
same original image can leak into validation/test sets, causing:
    - inflated accuracy
    - unrealistic similarity scores
    - data leakage

Therefore:
    split first
    augment train only

Default split ratios:
    train = 70%
    val   = 15%
    test  = 15%

Usage:
    python split_toolmark_dataset.py
"""

import random
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INPUT_DIR = Path("ai_engine/datasets/toolmark/processed_clean")

OUTPUT_DIR = Path("ai_engine/datasets/toolmark/split")

TRAIN_DIR = OUTPUT_DIR / "train"
VAL_DIR   = OUTPUT_DIR / "val"
TEST_DIR  = OUTPUT_DIR / "test"

# ---------------------------------------------------------------------------
# Split ratios
# ---------------------------------------------------------------------------
TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15

# Safety check
assert abs(TRAIN_RATIO + VAL_RATIO + TEST_RATIO - 1.0) < 1e-6

VALID_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}

# ---------------------------------------------------------------------------
# Main split function
# ---------------------------------------------------------------------------
def split_dataset():

    if not INPUT_DIR.exists():
        print(f"ERROR: input directory not found:\n  {INPUT_DIR}")
        return

    firearm_dirs = sorted(
        p for p in INPUT_DIR.iterdir()
        if p.is_dir()
    )

    if not firearm_dirs:
        print(f"ERROR: no firearm folders found in:\n  {INPUT_DIR}")
        return

    print(f"Found {len(firearm_dirs)} firearm label(s)\n")

    total_train = 0
    total_val   = 0
    total_test  = 0

    for firearm_dir in firearm_dirs:

        label = firearm_dir.name

        images = sorted([
            p for p in firearm_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_EXTS
        ])

        if len(images) < 3:
            print(f"WARNING: '{label}' has fewer than 3 images — skipping.")
            continue

        # Shuffle deterministically
        random.shuffle(images)

        n_total = len(images)

        n_train = int(n_total * TRAIN_RATIO)
        n_val   = int(n_total * VAL_RATIO)

        train_files = images[:n_train]
        val_files   = images[n_train:n_train + n_val]
        test_files  = images[n_train + n_val:]

        # Create output folders
        train_out = TRAIN_DIR / label
        val_out   = VAL_DIR   / label
        test_out  = TEST_DIR  / label

        train_out.mkdir(parents=True, exist_ok=True)
        val_out.mkdir(parents=True, exist_ok=True)
        test_out.mkdir(parents=True, exist_ok=True)

        # Copy files
        for f in train_files:
            shutil.copy2(f, train_out / f.name)

        for f in val_files:
            shutil.copy2(f, val_out / f.name)

        for f in test_files:
            shutil.copy2(f, test_out / f.name)

        total_train += len(train_files)
        total_val   += len(val_files)
        total_test  += len(test_files)

        print(
            f"[{label}] "
            f"train={len(train_files)} | "
            f"val={len(val_files)} | "
            f"test={len(test_files)}"
        )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("DATASET SPLIT SUMMARY")
    print(f"Train images : {total_train}")
    print(f"Val images   : {total_val}")
    print(f"Test images  : {total_test}")
    print(f"Output path  : {OUTPUT_DIR}")
    print("=" * 50)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    split_dataset()