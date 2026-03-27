import random
from pathlib import Path

import cv2
import torch
from torch.utils.data import Dataset


# ---------------------------------------------------------------------------
# SiameseFingerprintDataset
# ---------------------------------------------------------------------------
class SiameseFingerprintDataset(Dataset):
    """
    Custom PyTorch Dataset for Siamese Network training on fingerprint images.

    Pair generation strategy
    ------------------------
    Each call to __getitem__ randomly produces either:
      - A POSITIVE pair  (label = 1.0) : two different images of the SAME identity
      - A NEGATIVE pair  (label = 0.0) : one image each from TWO different identities

    The split is ~50 / 50, giving the contrastive / triplet loss a balanced
    training signal without any pre-built pair list (pairs are sampled on-the-fly).

    Normalization
    -------------
    Inside load_image:
        uint8 [0, 255]  →  /255.0  →  [0.0, 1.0]
        [0.0, 1.0]      →  (x − 0.5) / 0.5  →  [−1.0, 1.0]

    This satisfies the project report requirement:
        "normalize pixel values for model input compatibility"
    and matches the output range expected by a CNN with BatchNorm layers.

    Arguments
    ---------
    root_dir  : path to the split folder  (e.g.  augmented/train)
    size      : virtual dataset length — controls epoch size independently
                of the actual number of image files (default 50 000)
    transform : optional torchvision transform applied AFTER normalization
                (useful for test-time augmentation or future experiments)
    """

    VALID_EXTS = {".bmp", ".png", ".jpg", ".jpeg"}

    def __init__(self, root_dir, size: int = 50_000, transform=None):

        self.root_dir  = Path(root_dir)
        self.size      = size
        self.transform = transform

        if not self.root_dir.exists():
            raise FileNotFoundError(
                f"Dataset root not found: {self.root_dir}"
            )

        # Build identity → [image paths] map
        # Only keep identities that have at least 2 images so that
        # random.sample(..., 2) never raises a ValueError on positive pairs.
        self.identity_images: dict[str, list[Path]] = {}

        for identity_dir in sorted(self.root_dir.iterdir()):

            if not identity_dir.is_dir():
                continue

            images = [
                p for p in identity_dir.iterdir()
                if p.suffix.lower() in self.VALID_EXTS
            ]

            if len(images) >= 2:
                self.identity_images[identity_dir.name] = images

        self.identity_names = list(self.identity_images.keys())

        if len(self.identity_names) < 2:
            raise ValueError(
                f"Need at least 2 identities with ≥2 images each. "
                f"Found {len(self.identity_names)} in {self.root_dir}"
            )

        print(
            f"SiameseFingerprintDataset ready: "
            f"{len(self.identity_names)} identities | "
            f"virtual size = {self.size:,}"
        )

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        # Virtual length: decouples epoch size from the number of image files.
        # Pairs are sampled randomly in __getitem__, so any integer works.
        return self.size

    # ------------------------------------------------------------------
    def load_image(self, path: Path) -> torch.Tensor:
        """
        Load one fingerprint image and return a normalised float32 tensor.

        Pipeline:
            1. Read as grayscale uint8  (H, W)
            2. Scale  [0, 255] → [0.0, 1.0]   via  / 255.0
            3. Standardise [0.0, 1.0] → [−1.0, 1.0]  via  (x  − 0.5) / 0.5
            4. Convert to float32 tensor and add channel dim → (1, H, W)
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
        img = torch.from_numpy(img).unsqueeze(0)   # float32 already

        # Step 5 — optional extra transform
        if self.transform is not None:
            img = self.transform(img)

        return img

    # ------------------------------------------------------------------
    def __getitem__(self, idx):
        """
        Return (img1, img2, label) where label is a float32 scalar tensor.
            label = 1.0  →  same identity  (positive pair)
            label = 0.0  →  different identities (negative pair)

        Note: idx is intentionally unused because pairs are sampled randomly.
        Randomness across epochs is controlled by the DataLoader's
        worker_init_fn / generator seed set in train.py.
        """
        same = random.randint(0, 1)

        if same:
            # Positive pair — two DIFFERENT images of the SAME identity
            identity   = random.choice(self.identity_names)
            img1_path, img2_path = random.sample(
                self.identity_images[identity], 2
            )
            label = 1.0

        else:
            # Negative pair — one image each from TWO DIFFERENT identities
            id1, id2   = random.sample(self.identity_names, 2)
            img1_path  = random.choice(self.identity_images[id1])
            img2_path  = random.choice(self.identity_images[id2])
            label = 0.0

        img1 = self.load_image(img1_path)
        img2 = self.load_image(img2_path)

        return img1, img2, torch.tensor(label, dtype=torch.float32)


# ---------------------------------------------------------------------------
# Quick smoke-test  (run:  python siamese_dataset.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from torch.utils.data import DataLoader

    root = sys.argv[1] if len(sys.argv) > 1 else "ai_engine/datasets/augmented/train"

    dataset = SiameseFingerprintDataset(root_dir=root, size=100)
    loader  = DataLoader(dataset, batch_size=8, shuffle=False, num_workers=0)

    img1, img2, labels = next(iter(loader))

    print(f"img1 shape  : {img1.shape}")           # (8, 1, 224, 224)
    print(f"img2 shape  : {img2.shape}")           # (8, 1, 224, 224)
    print(f"labels      : {labels}")               # mix of 0.0 and 1.0
    print(f"img1 min/max: {img1.min():.3f} / {img1.max():.3f}")  # ≈ -1.0 / 1.0
    print(f"img2 min/max: {img2.min():.3f} / {img2.max():.3f}")
    print("Smoke-test passed.")