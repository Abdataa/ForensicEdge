"""
train_toolmark.py
-----------------
Trains the ForensicEdge Siamese network on the augmented breech-face
impression (tool-mark) dataset.  Designed to run on Google Colab (GPU)
connected via the VSCode Colab extension, with checkpoint saving so
training survives disconnections.

Differences from train_siamese.py (fingerprint training)
---------------------------------------------------------
| Setting               | Fingerprint           | Toolmark (this file)         |
|-----------------------|-----------------------|------------------------------|
| Dataset class         | SiameseFingerprintDataset | SiameseToolmarkDataset   |
| Model class           | SiameseNetwork        | SiameseToolmarkNetwork       |
| Loss class            | ContrastiveLoss       | ContrastiveLossToolmark      |
| EMBEDDING_DIM         | 256                   | 128                          |
| MATCH_THRESHOLD       | 85.0%                 | 80.0%                        |
| POSSIBLE_THRESHOLD    | 60.0%                 | 55.0%                        |
| MARGIN                | 1.0                   | 1.4  (see note below)        |
| Virtual train size    | 50 000                | 20 000                       |
| Virtual val size      | 10 000                | 4 000                        |
| EPOCHS                | 20                    | 30                           |
| Scheduler patience    | 3                     | 5                            |
| CHECKPOINT_DIR        | checkpoints/          | checkpoints/toolmark/        |

MARGIN = 1.4 — why this is critical
-------------------------------------
With 128-dim L2-normalised embeddings, random unit vectors cluster around
Euclidean distance ≈ 1.41.  Using margin=1.0 (fingerprint default) means
0% of negative pairs produce any gradient at epoch 1 — the model sees only
same-pair loss and all embeddings collapse.  margin=1.4 gives ~42% of
negative pairs inside the margin from the start, producing a balanced
gradient signal.  See loss_toolmark.py for the full derivation.

BEFORE RUNNING — split the flat augmented data into train/val/test
------------------------------------------------------------------
The augment_toolmark.py output is a flat layout:
    ai_engine/datasets/toolmark/augmented/firearmA/ ... firearmZ/

This script includes a split_toolmark_data() helper that creates:
    ai_engine/datasets/toolmark/augmented/train/
    ai_engine/datasets/toolmark/augmented/val/
    ai_engine/datasets/toolmark/augmented/test/
    ai_engine/datasets/toolmark/processed_clean/train/
    ai_engine/datasets/toolmark/processed_clean/val/
    ai_engine/datasets/toolmark/processed_clean/test/

Set RUN_SPLIT = True on the first run.  It is idempotent — safe to call
again if already split.  Set RUN_SPLIT = False on subsequent runs.

HOW TO RUN ON GOOGLE COLAB VIA VSCODE
=======================================

Step 1 — Open Colab from VSCode
    In VSCode, open the Command Palette (Ctrl+Shift+P / Cmd+Shift+P).
    Type: "Colab: Create New Notebook" or open an existing .ipynb file.
    Sign in with Google account when prompted.

Step 2 — Change runtime to GPU
    In the Colab notebook toolbar: Runtime → Change runtime type → T4 GPU → Save.

Step 3 — Mount Google Drive (to save checkpoints permanently)
    In the first Colab cell run:

        from google.colab import drive
        drive.mount('/content/drive')

    Then set CHECKPOINT_DIR below to Drive path, for example:
        CHECKPOINT_DIR = Path("/content/drive/MyDrive/ForensicEdge/checkpoints/toolmark")

Step 4 — Upload project to Colab
    Option A (recommended): Clone from GitHub
        !git clone https://github.com/Abdataa/ForensicEdge.git
        %cd ForensicEdge

    Option B: Upload a zip via Drive
        !unzip /content/drive/MyDrive/ForensicEdge.zip -d /content/ForensicEdge
        %cd /content/ForensicEdge

Step 5 — Install dependencies
    !pip install -q torch torchvision opencv-python-headless albumentations tqdm scipy

Step 6 — Run this script
    Either paste the entire file into a Colab cell, or run:
        !python ai_engine/training/train_toolmark.py

Step 7 — Resume from checkpoint after disconnection
    Set RESUME_FROM_CHECKPOINT = True below.
    Colab will load the last saved checkpoint and continue from that epoch.

CHECKPOINT STRATEGY
-------------------
Two files are saved to CHECKPOINT_DIR:

    best_model_toolmark.pth
        Saved whenever val loss improves.
        Use this file for inference and your FastAPI backend.
        Named distinctly from best_model.pth to avoid overwriting fingerprint weights.

    checkpoint_latest.pth
        Overwritten every CHECKPOINT_EVERY epochs.
        Contains full training state (epoch, weights, optimizer, scheduler,
        loss history) so training can resume exactly where it left off.

TQDM PROGRESS BARS
------------------
Three nested bars are shown during training:

    Epoch  1/30 ──────── [train=0.2841  val=0.2413  lr=1.00e-03  time=87.4s]
      Train  100%|████████████| 625/625 [01:21  loss=0.2841]
      Val    100%|████████████| 125/125 [00:11  loss=0.2413]

tqdm.auto is used so the bars render as rich notebook widgets on Colab
and as plain ASCII bars in a terminal — no code change needed between
environments.
"""

import random
import shutil
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm.auto import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_engine.training.siamese_toolmark_dataset import SiameseToolmarkDataset
from ai_engine.models.siamese_toolmark_network   import SiameseToolmarkNetwork
from ai_engine.models.loss_toolmark              import ContrastiveLossToolmark


# ===========================================================================
# CONFIG — all hyperparameters in one place
# ===========================================================================

# --- Data split control ---
# Set True on the FIRST run to split the flat augmented/ and processed_clean/
# folders into train / val / test subdirectories (80 / 10 / 10 split).
# Set False on all subsequent runs — split is idempotent but takes time.
RUN_SPLIT = False

# --- Data ---
# Flat source directories (output of augment_toolmark.py / enhance_toolmark.py)
AUGMENTED_FLAT_DIR     = Path("ai_engine/datasets/toolmark/augmented")
CLEAN_FLAT_DIR         = Path("ai_engine/datasets/toolmark/processed_clean")

# Split target directories (created by split_toolmark_data() below)
TRAIN_DIR = Path("ai_engine/datasets/toolmark/augmented")
VAL_DIR   = Path("ai_engine/datasets/toolmark/split/val")

# --- Model ---
EMBEDDING_DIM      = 128    # matches ToolmarkCNN / SiameseToolmarkNetwork defaults
MATCH_THRESHOLD    = 80.0   # tune via experiments/threshold_experiment.py
POSSIBLE_THRESHOLD = 55.0

# --- Loss ---
# CRITICAL: margin=1.4, NOT 1.0 (fingerprint default).
# With 128-dim embeddings, margin=1.0 gives 0% gradient on negatives → collapse.
# margin=1.4 gives ~42% of negative pairs inside the margin at initialisation.
# See loss_toolmark.py module docstring for the full derivation.
MARGIN = 1.4

# --- Training ---
BATCH_SIZE   = 32
EPOCHS       = 30      # 30 > 20 (fingerprint): small dataset benefits from
                       # longer training with LR decay catching diminishing returns
LR           = 1e-3
WEIGHT_DECAY = 1e-4    # L2 regularisation on Adam — unchanged from fingerprint
GRAD_CLIP    = 1.0     # max gradient norm — prevents explosion on hard pairs

# Virtual dataset sizes — smaller than fingerprint (50k/10k) because
# 24 classes means the model sees all label combinations much faster per epoch.
# Oversizing bloats epoch time without adding novel pair diversity.
TRAIN_VIRTUAL_SIZE = 20_000
VAL_VIRTUAL_SIZE   =  4_000

# --- DataLoader ---
NUM_WORKERS = 2
PIN_MEMORY  = True   # faster CPU → GPU transfer (only effective with GPU)

# --- Reproducibility ---
SEED = 42

# --- Checkpointing ---
# !! IMPORTANT FOR COLAB !!
# The /content/ filesystem is wiped on every disconnection.
# Change CHECKPOINT_DIR to a path inside Google Drive so checkpoints survive.
#
CHECKPOINT_DIR = Path("/kaggle/working/ForensicEdge/checkpoints/toolmark")
#
# Colab + Drive alternative:
# CHECKPOINT_DIR = Path("/content/drive/MyDrive/ForensicEdge/checkpoints/toolmark")
#
# Local alternative:
# CHECKPOINT_DIR = Path("ai_engine/models/weights/toolmark")
#
CHECKPOINT_EVERY       = 1      # save checkpoint_latest.pth every N epochs
RESUME_FROM_CHECKPOINT = False  # set True to resume after a disconnection

# Scheduler patience: 5 (was 3 for fingerprint).
# With only 24 classes and a smaller virtual dataset, val loss can be
# noisier epoch-to-epoch (fewer distinct pair configurations sampled).
# Extra patience avoids premature LR reductions that would stall training.
SCHEDULER_PATIENCE = 5

# --- Device ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===========================================================================


# ---------------------------------------------------------------------------
# Data split helper
# ---------------------------------------------------------------------------
def split_toolmark_data(
    src_dir:    Path,
    split_name: str,
    seed:       int = SEED,
    train_frac: float = 0.8,
    val_frac:   float = 0.1,
) -> None:
    """
    Split a flat toolmark directory (one subfolder per firearm label) into
    train / val / test subdirectories inside src_dir.

    Layout before:
        src_dir/
            firearmA/  *.png
            firearmB/  *.png
            ...

    Layout after:
        src_dir/
            train/firearmA/  ...
            train/firearmB/  ...
            val/firearmA/    ...
            val/firearmB/    ...
            test/firearmA/   ...
            test/firearmB/   ...

    The split is:
        train : train_frac        (default 80%)
        val   : val_frac          (default 10%)
        test  : 1 - train - val   (default 10%)

    Idempotent — if train/ already exists, skips the split and returns.
    All files are MOVED (not copied) to avoid doubling disk usage.

    Args:
        src_dir    : flat source directory to split
        split_name : human-readable name for progress messages (e.g. "augmented")
        seed       : random seed for reproducible split
        train_frac : fraction of images assigned to train
        val_frac   : fraction of images assigned to val
    """
    train_dir = src_dir / "train"

    if train_dir.exists():
        tqdm.write(
            f"  [{split_name}] train/ already exists — skipping split."
        )
        return

    rng = random.Random(seed)

    label_dirs = sorted(p for p in src_dir.iterdir() if p.is_dir())
    if not label_dirs:
        tqdm.write(f"  [{split_name}] WARNING: no subdirectories in {src_dir}")
        return

    for split in ("train", "val", "test"):
        (src_dir / split).mkdir(parents=True, exist_ok=True)

    total_moved = 0

    for label_dir in label_dirs:
        label = label_dir.name

        images = sorted(
            p for p in label_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
        )

        if not images:
            continue

        rng.shuffle(images)

        n_train = max(1, int(len(images) * train_frac))
        n_val   = max(1, int(len(images) * val_frac))
        # test gets the remainder — at least 1 if possible
        n_test  = max(0, len(images) - n_train - n_val)

        # Guard: ensure splits don't exceed total
        if n_train + n_val + n_test > len(images):
            n_test = len(images) - n_train - n_val

        splits_images = {
            "train": images[:n_train],
            "val":   images[n_train: n_train + n_val],
            "test":  images[n_train + n_val: n_train + n_val + n_test],
        }

        for split_name_inner, split_images in splits_images.items():
            dest_dir = src_dir / split_name_inner / label
            dest_dir.mkdir(parents=True, exist_ok=True)
            for img_path in split_images:
                shutil.move(str(img_path), str(dest_dir / img_path.name))
                total_moved += 1

        # Remove now-empty label directory
        try:
            label_dir.rmdir()
        except OSError:
            pass   # not empty if unexpected files present — leave it

    tqdm.write(
        f"  [{split_name}] Split complete — {total_moved} files → "
        f"train({train_frac:.0%}) / val({val_frac:.0%}) / "
        f"test({1 - train_frac - val_frac:.0%})"
    )


# ---------------------------------------------------------------------------
def set_seeds(seed: int) -> None:
    """Fix all random seeds for reproducible training runs."""
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
def build_dataloaders():
    """Create train and validation DataLoaders for toolmark data."""
    train_dataset = SiameseToolmarkDataset(
        root_dir = TRAIN_DIR,
        size     = TRAIN_VIRTUAL_SIZE,
    )
    val_dataset = SiameseToolmarkDataset(
        root_dir = VAL_DIR,
        size     = VAL_VIRTUAL_SIZE,
    )

    # Seeded generator makes DataLoader shuffle reproducible across runs
    g = torch.Generator()
    g.manual_seed(SEED)

    train_loader = DataLoader(
        train_dataset,
        batch_size  = BATCH_SIZE,
        shuffle     = True,
        num_workers = NUM_WORKERS,
        pin_memory  = PIN_MEMORY,
        generator   = g,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size  = BATCH_SIZE,
        shuffle     = False,
        num_workers = NUM_WORKERS,
        pin_memory  = PIN_MEMORY,
    )
    return train_loader, val_loader


# ---------------------------------------------------------------------------
def build_model():
    """
    Instantiate the toolmark Siamese model, loss function, optimizer,
    and LR scheduler.
    """
    model = SiameseToolmarkNetwork(
        embedding_dim      = EMBEDDING_DIM,
        match_threshold    = MATCH_THRESHOLD,
        possible_threshold = POSSIBLE_THRESHOLD,
    ).to(DEVICE)

    criterion = ContrastiveLossToolmark(margin=MARGIN)

    optimizer = optim.Adam(
        model.parameters(),
        lr           = LR,
        weight_decay = WEIGHT_DECAY,
    )

    # Halve LR when val loss stops improving for SCHEDULER_PATIENCE epochs.
    # patience=5 (fingerprint used 3) — gives more room for the noisier
    # val loss that comes with only 24 classes and 4 000 virtual pairs.
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode     = "min",
        factor   = 0.5,
        patience = SCHEDULER_PATIENCE,
    )

    return model, criterion, optimizer, scheduler


# ---------------------------------------------------------------------------
def save_checkpoint(
    epoch:         int,
    model:         nn.Module,
    optimizer:     optim.Optimizer,
    scheduler,
    best_val_loss: float,
    train_losses:  list,
    val_losses:    list,
    filename:      str = "checkpoint_latest.pth",
) -> None:
    """
    Save full training state to disk so training can resume after a
    Colab disconnection.

    Saved fields
    ------------
    epoch                : last completed epoch (resume starts at epoch + 1)
    model_state_dict     : model weights
    optimizer_state_dict : optimizer state (momentum buffers, per-param lr)
    scheduler_state_dict : scheduler state (patience counter, best loss seen)
    best_val_loss        : best validation loss achieved so far
    train_losses         : full list of per-epoch training losses
    val_losses           : full list of per-epoch validation losses
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / filename
    torch.save(
        {
            "epoch":                epoch,
            "model_state_dict":     model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "best_val_loss":        best_val_loss,
            "train_losses":         train_losses,
            "val_losses":           val_losses,
        },
        path,
    )
    tqdm.write(f"    Checkpoint saved → {path}")


# ---------------------------------------------------------------------------
def load_checkpoint(model, optimizer, scheduler):
    """
    Load checkpoint_latest.pth and restore full training state.
    Returns (start_epoch, best_val_loss, train_losses, val_losses).
    Raises FileNotFoundError with a clear message if no checkpoint exists.
    """
    path = CHECKPOINT_DIR / "checkpoint_latest.pth"
    if not path.exists():
        raise FileNotFoundError(
            f"No checkpoint found at {path}.\n"
            f"Set RESUME_FROM_CHECKPOINT = False to start fresh."
        )
    ckpt = torch.load(path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    tqdm.write(f"Resumed from epoch {ckpt['epoch']} — loaded {path}")
    return (
        ckpt["epoch"],
        ckpt["best_val_loss"],
        ckpt["train_losses"],
        ckpt["val_losses"],
    )


# ---------------------------------------------------------------------------
def train_epoch(model, loader, criterion, optimizer) -> float:
    """
    One full training pass over the toolmark dataset.

    Shows a tqdm batch bar:
        Train  100%|████████████| 625/625 [01:21  loss=0.2841]

    The loss shown is a running average over all batches — it falls as
    the epoch progresses if training is working correctly.

    Returns mean loss over all batches.
    """
    model.train()
    total_loss   = 0.0
    running_loss = 0.0

    with tqdm(
        loader,
        desc          = "  Train",
        leave         = False,
        unit          = "batch",
        dynamic_ncols = True,
    ) as batch_bar:

        for batch_idx, (img1, img2, label) in enumerate(batch_bar, start=1):

            img1  = img1.to(DEVICE,  non_blocking=True)
            img2  = img2.to(DEVICE,  non_blocking=True)
            label = label.to(DEVICE, non_blocking=True)

            optimizer.zero_grad()

            emb1, emb2 = model(img1, img2)
            loss = criterion(emb1, emb2, label)

            loss.backward()

            # Gradient clipping — prevents explosion on hard breech-face pairs
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRAD_CLIP)

            optimizer.step()

            total_loss   += loss.item()
            running_loss  = total_loss / batch_idx
            batch_bar.set_postfix(loss=f"{running_loss:.4f}")

    return total_loss / len(loader)


# ---------------------------------------------------------------------------
def validate(model, loader, criterion) -> float:
    """
    One full validation pass over the clean (non-augmented) toolmark val split.

    Shows a tqdm batch bar:
        Val    100%|████████████| 125/125 [00:11  loss=0.2413]

    Returns mean loss over all batches.
    """
    model.eval()
    total_loss   = 0.0
    running_loss = 0.0

    with torch.no_grad():
        with tqdm(
            loader,
            desc          = "  Val  ",
            leave         = False,
            unit          = "batch",
            dynamic_ncols = True,
        ) as batch_bar:

            for batch_idx, (img1, img2, label) in enumerate(batch_bar, start=1):

                img1  = img1.to(DEVICE,  non_blocking=True)
                img2  = img2.to(DEVICE,  non_blocking=True)
                label = label.to(DEVICE, non_blocking=True)

                emb1, emb2 = model(img1, img2)
                loss = criterion(emb1, emb2, label)

                total_loss   += loss.item()
                running_loss  = total_loss / batch_idx
                batch_bar.set_postfix(loss=f"{running_loss:.4f}")

    return total_loss / len(loader)


# ===========================================================================
# Main training loop
# ===========================================================================
def main():
    set_seeds(SEED)

    # --- Optional data split (run once before training) ---
    if RUN_SPLIT:
        print("Splitting toolmark data into train / val / test ...")
        split_toolmark_data(AUGMENTED_FLAT_DIR, split_name="augmented")
        split_toolmark_data(CLEAN_FLAT_DIR,     split_name="processed_clean")
        print()

    print("=" * 66)
    print("  ForensicEdge — Siamese Toolmark Network Training")
    print("=" * 66)
    print(f"  Device              : {DEVICE}")
    print(f"  Embedding dim       : {EMBEDDING_DIM}")
    print(f"  Epochs              : {EPOCHS}")
    print(f"  Batch size          : {BATCH_SIZE}")
    print(f"  LR                  : {LR}  "
          f"(ReduceLROnPlateau patience={SCHEDULER_PATIENCE} factor=0.5)")
    print(f"  Margin              : {MARGIN}  "
          f"(1.0 would collapse embeddings — see loss_toolmark.py)")
    print(f"  Grad clip           : {GRAD_CLIP}")
    print(f"  Train virtual size  : {TRAIN_VIRTUAL_SIZE:,}")
    print(f"  Val virtual size    : {VAL_VIRTUAL_SIZE:,}")
    print(f"  Checkpoint dir      : {CHECKPOINT_DIR}")
    print(f"  Save every          : {CHECKPOINT_EVERY} epoch(s)")
    print("=" * 66)
    print()

    train_loader, val_loader = build_dataloaders()
    model, criterion, optimizer, scheduler = build_model()

    # --- Resume or start fresh ---
    start_epoch   = 0
    best_val_loss = float("inf")
    train_losses: list[float] = []
    val_losses:   list[float] = []

    if RESUME_FROM_CHECKPOINT:
        start_epoch, best_val_loss, train_losses, val_losses = load_checkpoint(
            model, optimizer, scheduler
        )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    last_lr = optimizer.param_groups[0]["lr"]

    # --- Outer epoch progress bar ---
    with tqdm(
        range(start_epoch, EPOCHS),
        desc          = "Epoch",
        unit          = "epoch",
        leave         = True,
        dynamic_ncols = True,
    ) as epoch_bar:

        for epoch in epoch_bar:

            t0 = time.time()

            train_loss = train_epoch(model, train_loader, criterion, optimizer)
            val_loss   = validate(model, val_loader, criterion)

            # Step the scheduler AFTER val loss is known for this epoch
            scheduler.step(val_loss)

            current_lr = optimizer.param_groups[0]["lr"]

            # Notify when the scheduler fires and reduces the LR
            if current_lr != last_lr:
                tqdm.write(
                    f"  ↓ LR reduced: {last_lr:.2e} → {current_lr:.2e}  "
                    f"(val_loss={val_loss:.4f}  patience={SCHEDULER_PATIENCE})"
                )

            last_lr = current_lr
            elapsed = time.time() - t0

            train_losses.append(train_loss)
            val_losses.append(val_loss)

            # Update the outer epoch bar with final epoch metrics
            epoch_bar.set_postfix(
                train = f"{train_loss:.4f}",
                val   = f"{val_loss:.4f}",
                lr    = f"{current_lr:.2e}",
                time  = f"{elapsed:.1f}s",
            )

            # Save best model — used for inference and the FastAPI backend.
            # Named best_model_toolmark.pth to avoid overwriting fingerprint weights.
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(
                    model.state_dict(),
                    CHECKPOINT_DIR / "best_model_toolmark.pth",
                )
                tqdm.write(
                    f"  ✓ Best toolmark model saved  "
                    f"epoch={epoch + 1}  val_loss={best_val_loss:.4f}"
                )

            # Save full resumable checkpoint every CHECKPOINT_EVERY epochs
            if (epoch + 1) % CHECKPOINT_EVERY == 0:
                save_checkpoint(
                    epoch          = epoch + 1,
                    model          = model,
                    optimizer      = optimizer,
                    scheduler      = scheduler,
                    best_val_loss  = best_val_loss,
                    train_losses   = train_losses,
                    val_losses     = val_losses,
                )

    # --- Final summary ---
    print()
    print("=" * 66)
    print("  Training complete")
    print(f"  Best val loss       : {best_val_loss:.4f}")
    print(f"  Best model          : {CHECKPOINT_DIR / 'best_model_toolmark.pth'}")
    print(f"  Loss history        : {len(train_losses)} epochs recorded")
    print("=" * 66)


if __name__ == "__main__":
    main()