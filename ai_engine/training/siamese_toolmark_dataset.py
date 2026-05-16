"""
siamese_toolmark_dataset.py
===========================
PyTorch Dataset for Siamese Network training on breech-face impression
(tool-mark) images produced by enhance_toolmark.py / augment_toolmark.py.

Adapted from siamese_dataset.py (fingerprint pipeline) but re-designed
around the toolmark data structure:

Key differences from the fingerprint dataset
---------------------------------------------
| Aspect               | Fingerprint               | Toolmark (this file)         |
|----------------------|---------------------------|------------------------------|
| Identity concept     | Person / finger           | Firearm (firearmA … firearmZ)|
| Class count          | Thousands                 | 24 labels (very small)       |
| Positive pair        | Same person, diff image   | Same firearm, diff cartridge |
| Negative pair        | Two different people      | Two different firearms       |
| Split structure      | augmented/train/          | augmented/<label>/  (flat)   |
| Images per class     | Many (after 6× augment)   | ~100 originals → 600+ aug    |

Because there are only 24 firearm labels, the negative pair sampler
explicitly ensures id1 ≠ id2 (instead of relying on random.sample giving
distinct values from a pool of thousands).

Pair generation strategy
------------------------
Each __getitem__ call randomly produces:
  - POSITIVE pair  (label = 1.0): two images from the SAME firearm label
  - NEGATIVE pair  (label = 0.0): one image each from TWO DIFFERENT labels

The 50/50 split is enforced by a coin-flip, giving the contrastive loss a
balanced training signal without any pre-built pair list.

Normalisation (identical to fingerprint pipeline)
-------------------------------------------------
    uint8 [0, 255]  →  / 255.0  →  [0.0, 1.0]
    [0.0, 1.0]      →  (x − 0.5) / 0.5  →  [−1.0, 1.0]

Arguments
---------
root_dir  : path to the augmented toolmark folder
            (e.g. "ai_engine/datasets/toolmark/augmented")
            Contains one subdirectory per firearm label.
size      : virtual dataset length — controls epoch size independently
            of the actual file count (default 20 000; smaller than the
            fingerprint default of 50 000 because there are only 24 classes)
transform : optional torchvision transform applied AFTER normalisation

Usage
-----
    python siamese_toolmark_dataset.py
    python siamese_toolmark_dataset.py ai_engine/datasets/toolmark/augmented
"""

import random
from pathlib import Path

import cv2
import torch
from torch.utils.data import Dataset


# ---------------------------------------------------------------------------
# SiameseToolmarkDataset
# ---------------------------------------------------------------------------
class SiameseToolmarkDataset(Dataset):
    """
    Siamese pair dataset for breech-face impression (tool-mark) images.

    Each sample is a triplet (img1, img2, label):
        label = 1.0  →  same firearm  (positive pair)
        label = 0.0  →  different firearms (negative pair)
    """

    VALID_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}

    def __init__(
        self,
        root_dir,
        size: int = 20_000,
        transform=None,
    ):
        """
        Args:
            root_dir  : directory containing one subfolder per firearm label.
                        Each subfolder holds the preprocessed PNG images for
                        that firearm (originals + augmented copies).
            size      : virtual epoch length (pairs are sampled on-the-fly).
                        Default 20 000 — smaller than the fingerprint default
                        because toolmark has only 24 classes, so the model sees
                        a full coverage of all label combinations much faster.
            transform : optional torchvision transform applied AFTER the
                        built-in [0,255] → [−1,1] normalisation step.
        """
        self.root_dir  = Path(root_dir)
        self.size      = size
        self.transform = transform

        if not self.root_dir.exists():
            raise FileNotFoundError(
                f"Dataset root not found: {self.root_dir}\n"
                f"Run enhance_toolmark.py then augment_toolmark.py first."
            )

        # Build  firearm_label → [list of image Paths]
        # Only keep labels that have ≥ 2 images so random.sample(..., 2)
        # never raises ValueError when building positive pairs.
        self.label_images: dict[str, list[Path]] = {}

        for label_dir in sorted(self.root_dir.iterdir()):

            if not label_dir.is_dir():
                continue

            images = [
                p for p in label_dir.iterdir()
                if p.is_file() and p.suffix.lower() in self.VALID_EXTS
            ]

            if len(images) >= 2:
                self.label_images[label_dir.name] = sorted(images)
            else:
                print(
                    f"  WARNING: '{label_dir.name}' has {len(images)} image(s) "
                    f"— need ≥ 2 for positive pairs. Skipping."
                )

        self.label_names = list(self.label_images.keys())

        # With only 24 firearm labels, we need ≥ 2 labels for negative pairs.
        if len(self.label_names) < 2:
            raise ValueError(
                f"Need at least 2 firearm labels with ≥ 2 images each. "
                f"Found {len(self.label_names)} qualifying label(s) in "
                f"{self.root_dir}.\n"
                f"Run augment_toolmark.py to generate enough training images."
            )

        # Summary counts
        total_images = sum(len(v) for v in self.label_images.values())
        print(
            f"SiameseToolmarkDataset ready:\n"
            f"  Labels (firearms) : {len(self.label_names)}\n"
            f"  Total images      : {total_images:,}\n"
            f"  Virtual epoch size: {self.size:,}\n"
            f"  Root              : {self.root_dir}"
        )

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        # Virtual length: decouples epoch size from the actual file count.
        # Pairs are sampled on-the-fly in __getitem__, so any integer works.
        return self.size

    # ------------------------------------------------------------------
    def load_image(self, path: Path) -> torch.Tensor:
        """
        Load one toolmark image and return a normalised float32 tensor.

        Pipeline (identical to fingerprint siamese_dataset.py):
            1. Read as grayscale uint8  →  (H, W)
            2. Scale  [0, 255]   →  [0.0, 1.0]   via  / 255.0
            3. Standardise       →  [−1.0, 1.0]  via  (x − 0.5) / 0.5
            4. Convert to float32 tensor, add channel dim  →  (1, H, W)
            5. Apply optional extra transform if provided
        """
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

        if img is None:
            raise ValueError(
                f"cv2.imread returned None for: {path}\n"
                f"The file may be corrupt or the path may be wrong."
            )

        # Step 2 — scale to [0.0, 1.0]
        img = img.astype("float32") / 255.0

        # Step 3 — standardise to [−1.0, 1.0]
        img = (img - 0.5) / 0.5

        # Step 4 — tensor (1, H, W)
        img = torch.from_numpy(img).unsqueeze(0)   # already float32

        # Step 5 — optional extra transform
        if self.transform is not None:
            img = self.transform(img)

        return img

    # ------------------------------------------------------------------
    def __getitem__(self, idx):
        """
        Return (img1, img2, label) where label is a float32 scalar tensor.

            label = 1.0  →  same firearm   (positive pair)
            label = 0.0  →  different firearms (negative pair)

        Note: idx is intentionally unused because pairs are sampled randomly.
        The 50/50 coin-flip ensures a balanced positive/negative ratio across
        the epoch regardless of how many images each label has.

        Negative-pair sampling explicitly checks id1 ≠ id2.  This guard is
        essential here because there are only 24 labels — with a small pool,
        naive random.sample could in principle (though unlikely) still be
        tricked by edge cases during DataLoader multi-worker initialisation.
        """
        same = random.randint(0, 1)

        if same:
            # --- Positive pair: two DIFFERENT images of the SAME firearm ---
            label_name = random.choice(self.label_names)
            img1_path, img2_path = random.sample(
                self.label_images[label_name], 2
            )
            label = 1.0

        else:
            # --- Negative pair: one image each from TWO DIFFERENT firearms ---
            # Explicit id1 ≠ id2 check — critical with only 24 labels.
            id1 = random.choice(self.label_names)
            id2 = random.choice(self.label_names)
            while id2 == id1:
                id2 = random.choice(self.label_names)

            img1_path = random.choice(self.label_images[id1])
            img2_path = random.choice(self.label_images[id2])
            label = 0.0

        img1 = self.load_image(img1_path)
        img2 = self.load_image(img2_path)

        return img1, img2, torch.tensor(label, dtype=torch.float32)


# ---------------------------------------------------------------------------
# Quick smoke-test  (run:  python siamese_toolmark_dataset.py [root_dir])
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from torch.utils.data import DataLoader

    root = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "ai_engine/datasets/toolmark/augmented"
    )

    # --- Dataset construction ---
    dataset = SiameseToolmarkDataset(root_dir=root, size=100)
    loader  = DataLoader(dataset, batch_size=8, shuffle=False, num_workers=0)

    # --- One batch check ---
    img1, img2, labels = next(iter(loader))

    print(f"\nBatch checks:")
    print(f"  img1 shape   : {img1.shape}")           # (8, 1, 224, 224)
    print(f"  img2 shape   : {img2.shape}")           # (8, 1, 224, 224)
    print(f"  labels       : {labels}")               # mix of 0.0 and 1.0
    print(f"  img1 min/max : {img1.min():.3f} / {img1.max():.3f}")  # ≈ -1.0 / 1.0
    print(f"  img2 min/max : {img2.min():.3f} / {img2.max():.3f}")

    # --- Pair-balance check across 200 samples ---
    positives = 0
    negatives = 0
    for _, _, lbl in DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0):
        if lbl.item() == 1.0:
            positives += 1
        else:
            negatives += 1
        if positives + negatives >= 200:
            break

    print(f"\nPair-balance check (200 samples):")
    print(f"  Positives (same firearm)      : {positives}")
    print(f"  Negatives (different firearms): {negatives}")
    print(f"  Ratio                         : {positives / max(negatives, 1):.2f}  (target ≈ 1.0)")

    print("\nSmoke-test passed.")