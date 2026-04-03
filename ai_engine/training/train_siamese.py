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
    Sign in with Google account when prompted.

Step 2 — Change runtime to GPU
    In the Colab notebook toolbar: Runtime → Change runtime type → T4 GPU → Save.

Step 3 — Mount Google Drive (to save checkpoints permanently)
    In the first Colab cell run:

        from google.colab import drive
        drive.mount('/content/drive')

    Then set CHECKPOINT_DIR below to Drive path, for example:
        CHECKPOINT_DIR = Path("/content/drive/MyDrive/ForensicEdge/checkpoints")

Step 4 — Upload  project to Colab
    Option A (recommended): Clone from GitHub
        !git clone https://github.com/Abdataa/ForensicEdge.git
        %cd ForensicEdge

    Option B: Upload a zip via Drive
        !unzip /content/drive/MyDrive/ForensicEdge.zip -d /content/ForensicEdge
        %cd /content/ForensicEdge

Step 5 — Install dependencies
    !pip install -q torch torchvision opencv-python-headless albumentations tqdm

Step 6 — Run this script
    Either paste the entire file into a Colab cell, or run:
        !python ai_engine/training/train_siamese.py

Step 7 — Resume from checkpoint after disconnection
    Set RESUME_FROM_CHECKPOINT = True below.
    Colab will load the last saved checkpoint and continue from that epoch.

CHECKPOINT STRATEGY
-------------------
Two files are saved to CHECKPOINT_DIR:

    best_model.pth
        Saved whenever val loss improves.
        Use this file for inference and your FastAPI backend.

    checkpoint_latest.pth
        Overwritten every CHECKPOINT_EVERY epochs.
        Contains full training state (epoch, weights, optimizer, scheduler,
        loss history) so training can resume exactly where it left off.

TQDM PROGRESS BARS
------------------
Three nested bars are shown during training:

    Epoch  1/20 ──────── [train=0.3421  val=0.2918  lr=1.00e-03  time=141.3s]
      Train  100%|████████████| 1562/1562 [02:14  loss=0.3421]
      Val    100%|████████████|  312/312  [00:27  loss=0.2918]

tqdm.auto is used so the bars render as rich notebook widgets on Colab
and as plain ASCII bars in a terminal — no code change needed between
environments.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from pathlib import Path

# tqdm.auto: rich notebook widget on Colab, plain ASCII bar in terminal
# No code change needed when switching between environments
from tqdm.auto import tqdm

from ai_engine.training.siamese_dataset import SiameseFingerprintDataset
from ai_engine.models.siamese_network    import SiameseNetwork
from ai_engine.models.loss_functions     import ContrastiveLoss


# ===========================================================================
# CONFIG — all hyperparameters in one place
# ===========================================================================

# --- Data ---
# Training uses augmented data (4× original size, realistic distortions).
# Val / Test use processed_clean — no augmentation for a clean eval signal.
TRAIN_DIR = Path("ai_engine/datasets/augmented/train")
VAL_DIR   = Path("ai_engine/datasets/processed_clean/val")

# --- Model ---
EMBEDDING_DIM      = 256     # must match cnn_feature_extractor.py default
MATCH_THRESHOLD    = 85.0    # tune via experiments/threshold_experiment.py
POSSIBLE_THRESHOLD = 60.0

# --- Loss ---
# margin=1.0 is standard for L2-normalised embeddings (max Euclidean dist = 2.0)
# margin=2.0 pushes negatives to maximum distance → extreme gradients early on
MARGIN = 1.0

# --- Training ---
BATCH_SIZE   = 32
EPOCHS       = 20      # scheduler handles LR decay so more epochs are useful
LR           = 1e-3
WEIGHT_DECAY = 1e-4    # L2 regularisation on Adam
GRAD_CLIP    = 1.0     # max gradient norm — prevents gradient explosion

# --- DataLoader ---
# num_workers > 0 prefetches batches so the GPU stays fed between steps.
# Set NUM_WORKERS = 0 if you hit "RuntimeError: DataLoader worker" locally.
NUM_WORKERS = 2
PIN_MEMORY  = True     # faster CPU → GPU transfer (only effective with GPU)

# --- Reproducibility ---
SEED = 42

# --- Checkpointing ---
# !! IMPORTANT FOR COLAB !!
# The /content/ filesystem is wiped on every disconnection.
# Change CHECKPOINT_DIR to a path inside Google Drive so checkpoints survive.
#
#   CHECKPOINT_DIR = Path("/content/drive/MyDrive/ForensicEdge/checkpoints")
#
CHECKPOINT_DIR         = Path("/content/drive/MyDrive/ForensicEdge/checkpoints")
CHECKPOINT_EVERY       = 5      # save checkpoint_latest.pth every N epochs
RESUME_FROM_CHECKPOINT = False  # set True to resume after a disconnection

# --- Device ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===========================================================================


def set_seeds(seed: int) -> None:
    """Fix all random seeds for reproducible training runs."""
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
def build_dataloaders():
    """Create train and validation DataLoaders."""
    train_dataset = SiameseFingerprintDataset(root_dir=TRAIN_DIR, size=50_000)
    val_dataset   = SiameseFingerprintDataset(root_dir=VAL_DIR,   size=10_000)

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
    """Instantiate model, loss function, optimizer, and LR scheduler."""
    model = SiameseNetwork(
        embedding_dim      = EMBEDDING_DIM,
        match_threshold    = MATCH_THRESHOLD,
        possible_threshold = POSSIBLE_THRESHOLD,
    ).to(DEVICE)

    criterion = ContrastiveLoss(margin=MARGIN)

    optimizer = optim.Adam(
        model.parameters(),
        lr           = LR,
        weight_decay = WEIGHT_DECAY,
    )

    # Halve LR when val loss stops improving for 3 consecutive epochs.
    # verbose=True prints a message each time the LR is reduced.
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode     = "min",
        factor   = 0.5,
        patience = 3,
        verbose  = True,
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
    # tqdm.write prints without breaking the progress bars
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
    One full training pass over the dataset.

    Shows a tqdm batch bar:
        Train  100%|████████████| 1562/1562 [02:14  loss=0.3421]

    The loss shown is a running average over all batches in this epoch —
    it falls as the epoch progresses if training is working correctly.

    Returns mean loss over all batches.
    """
    model.train()
    total_loss   = 0.0
    running_loss = 0.0

    # leave=False: bar disappears after the epoch so the outer epoch bar
    # remains visible and the terminal does not scroll endlessly
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

            # Gradient clipping — prevents gradient explosion on hard pairs
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRAD_CLIP)

            optimizer.step()

            total_loss   += loss.item()
            running_loss  = total_loss / batch_idx

            # Live running average loss on the right of the bar
            batch_bar.set_postfix(loss=f"{running_loss:.4f}")

    return total_loss / len(loader)


# ---------------------------------------------------------------------------
def validate(model, loader, criterion) -> float:
    """
    One full validation pass.

    Shows a tqdm batch bar:
        Val    100%|████████████|  312/312  [00:27  loss=0.2918]

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

    print("=" * 62)
    print("  ForensicEdge — Siamese Network Training")
    print("=" * 62)
    print(f"  Device         : {DEVICE}")
    print(f"  Embedding dim  : {EMBEDDING_DIM}")
    print(f"  Epochs         : {EPOCHS}")
    print(f"  Batch size     : {BATCH_SIZE}")
    print(f"  LR             : {LR}  (ReduceLROnPlateau patience=3 factor=0.5)")
    print(f"  Margin         : {MARGIN}")
    print(f"  Grad clip      : {GRAD_CLIP}")
    print(f"  Checkpoint dir : {CHECKPOINT_DIR}")
    print(f"  Save every     : {CHECKPOINT_EVERY} epochs")
    print("=" * 62)
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

    # --- Outer epoch progress bar ---
    # leave=True: stays visible after all epochs so the full history is readable.
    # tqdm.write() is used inside the loop so print statements don't break bars.
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

            # Step scheduler after val loss is known for this epoch
            scheduler.step(val_loss)

            elapsed    = time.time() - t0
            current_lr = optimizer.param_groups[0]["lr"]

            train_losses.append(train_loss)
            val_losses.append(val_loss)

            # Update the outer epoch bar right side with final epoch metrics
            epoch_bar.set_postfix(
                train = f"{train_loss:.4f}",
                val   = f"{val_loss:.4f}",
                lr    = f"{current_lr:.2e}",
                time  = f"{elapsed:.1f}s",
            )

            # Save best model — used for inference and FastAPI backend
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(
                    model.state_dict(),
                    CHECKPOINT_DIR / "best_model.pth",
                )
                # tqdm.write prints without breaking the progress bars
                tqdm.write(
                    f"  ✓ Best model saved  "
                    f"epoch={epoch + 1}  val_loss={best_val_loss:.4f}"
                )

            # Save resumable checkpoint every CHECKPOINT_EVERY epochs
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
    print("=" * 62)
    print("  Training complete")
    print(f"  Best val loss  : {best_val_loss:.4f}")
    print(f"  Best model     : {CHECKPOINT_DIR / 'best_model.pth'}")
    print("=" * 62)


if __name__ == "__main__":
    main()
