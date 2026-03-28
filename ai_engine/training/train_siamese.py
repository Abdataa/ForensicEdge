"""
train_siamese.py
----------------
Trains the ForensicEdge Siamese network on the augmented SOCOFing fingerprint
dataset.  Designed to run on Google Colab (GPU) connected via the VSCode
Colab extension, with checkpoint saving so training survives disconnections.

HOW TO RUN ON GOOGLE COLAB VIA VSCODE
=======================================

Step 1 — Open Colab from VSCode
    In VSCode, open the Command Palette (Ctrl+Shift+P / Cmd+Shift+P).
    Type: "Colab: Create New Notebook" or open an existing .ipynb file.
    Sign in with your Google account when prompted.

Step 2 — Change runtime to GPU
    In the Colab notebook toolbar: Runtime → Change runtime type → T4 GPU → Save.

Step 3 — Mount Google Drive (to save checkpoints permanently)
    In the first Colab cell run:

        from google.colab import drive
        drive.mount('/content/drive')

    Then set CHECKPOINT_DIR below to a path inside your Drive, for example:
        CHECKPOINT_DIR = Path("/content/drive/MyDrive/ForensicEdge/checkpoints")

Step 4 — Upload your project to Colab
    Option A (recommended): Clone from GitHub
        !git clone https://github.com/YOUR_USERNAME/ForensicEdge.git
        %cd ForensicEdge

    Option B: Upload a zip via Drive
        !unzip /content/drive/MyDrive/ForensicEdge.zip -d /content/ForensicEdge
        %cd /content/ForensicEdge

Step 5 — Install dependencies
    !pip install -q torch torchvision opencv-python-headless albumentations

Step 6 — Run this script
    Either paste the entire file into a Colab cell, or run:
        !python ai_engine/training/train_siamese.py

Step 7 — Resume from checkpoint after disconnection
    Set RESUME_FROM_CHECKPOINT = True below.
    Colab will load the last saved checkpoint and continue from that epoch.

CHECKPOINT STRATEGY
-------------------
Two files are saved to CHECKPOINT_DIR:
    best_model.pth      — saved whenever val loss improves (use for inference)
    checkpoint_latest.pth — overwritten every CHECKPOINT_EVERY epochs
                            (use to resume training after disconnection)

checkpoint_latest.pth contains:
    epoch, model_state_dict, optimizer_state_dict,
    scheduler_state_dict, best_val_loss, train_losses, val_losses
"""

import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from pathlib import Path

# ---------------------------------------------------------------------------
# Adjust import style depending on how you run this:
#   - As a module from project root:  python -m ai_engine.training.train_siamese
#   - As a script from project root:  python ai_engine/training/train_siamese.py
# ---------------------------------------------------------------------------
from ai_engine.datasets.siamese_dataset import SiameseFingerprintDataset
from ai_engine.models.siamese_network    import SiameseNetwork
from ai_engine.models.loss_functions     import ContrastiveLoss


# ===========================================================================
# CONFIG  — all hyperparameters in one place
# ===========================================================================

# --- Data ---
# Training uses augmented data (4x original size, realistic distortions)
# Val/Test use processed_clean (no augmentation — clean evaluation signal)
TRAIN_DIR = Path("ai_engine/datasets/augmented/train")
VAL_DIR   = Path("ai_engine/datasets/processed_clean/val")

# --- Model ---
EMBEDDING_DIM      = 256    # must match cnn_feature_extractor.py default
MATCH_THRESHOLD    = 85.0   # tune via experiments/threshold_experiment.py
POSSIBLE_THRESHOLD = 60.0

# --- Loss ---
# margin=1.0 is standard for L2-normalised embeddings (max distance = 2.0)
# margin=2.0 pushes negatives to maximum distance → extreme gradients early on
MARGIN = 1.0

# --- Training ---
BATCH_SIZE    = 32
EPOCHS        = 20     # increased from 10; scheduler handles LR decay
LR            = 1e-3
WEIGHT_DECAY  = 1e-4   # L2 regularisation on optimizer
GRAD_CLIP     = 1.0    # max gradient norm — prevents gradient explosion

# --- DataLoader ---
# num_workers > 0 enables prefetching so GPU stays fed between batches
# Set to 0 if you hit "RuntimeError: DataLoader worker" on Windows locally
NUM_WORKERS = 2
PIN_MEMORY  = True     # faster CPU→GPU transfer (only useful with GPU)

# --- Reproducibility ---
SEED = 42

# --- Checkpointing ---
# On Colab: set this to a path inside Google Drive so files survive disconnection
# Example: Path("/content/drive/MyDrive/ForensicEdge/checkpoints")
CHECKPOINT_DIR         = Path("ai_engine/models/weights")
CHECKPOINT_EVERY       = 5      # save checkpoint every N epochs
RESUME_FROM_CHECKPOINT = False  # set True to continue after a disconnection

# --- Device ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===========================================================================


def set_seeds(seed: int) -> None:
    """Fix all random seeds for reproducible training runs."""
    import random, numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_dataloaders():
    """Create train and validation DataLoaders."""
    train_dataset = SiameseFingerprintDataset(
        root_dir = TRAIN_DIR,
        size     = 50_000,   # virtual epoch size
    )
    val_dataset = SiameseFingerprintDataset(
        root_dir = VAL_DIR,
        size     = 10_000,
    )

    # Seeded generator so DataLoader shuffle is reproducible
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


def build_model():
    """Instantiate model, loss, optimizer, and LR scheduler."""
    model = SiameseNetwork(
        embedding_dim      = EMBEDDING_DIM,
        match_threshold    = MATCH_THRESHOLD,
        possible_threshold = POSSIBLE_THRESHOLD,
    ).to(DEVICE)

    criterion = ContrastiveLoss(margin=MARGIN)

    optimizer = optim.Adam(
        model.parameters(),
        lr           = LR,
        weight_decay = WEIGHT_DECAY,   # L2 regularisation
    )

    # Halve LR when val loss stops improving for 3 consecutive epochs
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode     = "min",
        factor   = 0.5,
        patience = 3,
        verbose  = True,
    )

    return model, criterion, optimizer, scheduler


def save_checkpoint(
    epoch:       int,
    model:       nn.Module,
    optimizer:   optim.Optimizer,
    scheduler,
    best_val_loss: float,
    train_losses:  list,
    val_losses:    list,
    filename:    str = "checkpoint_latest.pth",
) -> None:
    """
    Save full training state so training can resume after a Colab disconnection.
    Saves: epoch, model weights, optimizer state, scheduler state,
           best val loss so far, and the full loss history.
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
    print(f"  Checkpoint saved → {path}")


def load_checkpoint(model, optimizer, scheduler):
    """
    Load training state from checkpoint_latest.pth to resume training.
    Returns (start_epoch, best_val_loss, train_losses, val_losses).
    """
    path = CHECKPOINT_DIR / "checkpoint_latest.pth"
    if not path.exists():
        raise FileNotFoundError(
            f"No checkpoint found at {path}. "
            f"Set RESUME_FROM_CHECKPOINT = False to start fresh."
        )
    ckpt = torch.load(path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    print(f"Resumed from epoch {ckpt['epoch']} — {path}")
    return (
        ckpt["epoch"],
        ckpt["best_val_loss"],
        ckpt["train_losses"],
        ckpt["val_losses"],
    )


def train_epoch(model, loader, criterion, optimizer) -> float:
    """One full pass over the training set. Returns mean loss."""
    model.train()
    total_loss = 0.0

    for img1, img2, label in loader:
        img1  = img1.to(DEVICE, non_blocking=True)
        img2  = img2.to(DEVICE, non_blocking=True)
        label = label.to(DEVICE, non_blocking=True)

        optimizer.zero_grad()

        emb1, emb2 = model(img1, img2)
        loss = criterion(emb1, emb2, label)

        loss.backward()

        # Gradient clipping — prevents gradient explosion on hard pairs
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRAD_CLIP)

        optimizer.step()
        total_loss += loss.item()

    return total_loss / len(loader)


def validate(model, loader, criterion) -> float:
    """One full pass over the validation set. Returns mean loss."""
    model.eval()
    total_loss = 0.0

    with torch.no_grad():
        for img1, img2, label in loader:
            img1  = img1.to(DEVICE, non_blocking=True)
            img2  = img2.to(DEVICE, non_blocking=True)
            label = label.to(DEVICE, non_blocking=True)

            emb1, emb2 = model(img1, img2)
            loss = criterion(emb1, emb2, label)
            total_loss += loss.item()

    return total_loss / len(loader)


# ===========================================================================
# Main training loop
# ===========================================================================
def main():
    set_seeds(SEED)

    print(f"Device        : {DEVICE}")
    print(f"Embedding dim : {EMBEDDING_DIM}")
    print(f"Epochs        : {EPOCHS}")
    print(f"Batch size    : {BATCH_SIZE}")
    print(f"LR            : {LR}  (ReduceLROnPlateau patience=3, factor=0.5)")
    print(f"Margin        : {MARGIN}")
    print(f"Checkpoints   : {CHECKPOINT_DIR}")
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

    # --- Epoch loop ---
    for epoch in range(start_epoch, EPOCHS):

        t0 = time.time()

        train_loss = train_epoch(model, train_loader, criterion, optimizer)
        val_loss   = validate(model, val_loader, criterion)

        # Step LR scheduler — reduces LR when val loss plateaus
        scheduler.step(val_loss)

        elapsed = time.time() - t0
        current_lr = optimizer.param_groups[0]["lr"]

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        print(
            f"Epoch [{epoch+1:>2}/{EPOCHS}] | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"LR: {current_lr:.2e} | "
            f"Time: {elapsed:.1f}s"
        )

        # Save best model (for inference)
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), CHECKPOINT_DIR / "best_model.pth")
            print(f"  Best model saved (val loss: {best_val_loss:.4f})")

        # Save resumable checkpoint every N epochs
        if (epoch + 1) % CHECKPOINT_EVERY == 0:
            save_checkpoint(
                epoch       = epoch + 1,
                model       = model,
                optimizer   = optimizer,
                scheduler   = scheduler,
                best_val_loss  = best_val_loss,
                train_losses   = train_losses,
                val_losses     = val_losses,
            )

    print()
    print(f"Training complete. Best val loss: {best_val_loss:.4f}")
    print(f"Best model saved to: {CHECKPOINT_DIR / 'best_model.pth'}")


if __name__ == "__main__":
    main()