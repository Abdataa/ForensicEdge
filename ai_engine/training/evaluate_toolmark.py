"""
ai_engine/training/evaluate_toolmark.py
-----------------------------------------
Evaluates the trained ForensicEdge Siamese toolmark network on the held-out
test set and produces all metrics required by the project report:

    Accuracy, Precision, Recall, False Match Rate (FMR),
    False Non-Match Rate (FNMR), F1, AUC, EER,
    Confusion Matrix, ROC Curve, Similarity Distribution plot.

Differences from evaluate.py (fingerprint pipeline)
-----------------------------------------------------
| Aspect                  | Fingerprint evaluate.py      | evaluate_toolmark.py         |
|-------------------------|------------------------------|------------------------------|
| Model                   | SiameseNetwork               | SiameseToolmarkNetwork       |
| Metrics module          | metrics.py                   | metrics_toolmark.py          |
| TEST_DIR                | processed_clean/test         | toolmark/processed_clean/test|
| WEIGHTS_PATH            | best_model.pth               | best_model_toolmark.pth      |
| RESULTS_DIR             | docs/Experiment_Results      | docs/Experiment_Results/     |
|                         |                              |   toolmark                   |
| EMBEDDING_DIM           | 256                          | 128                          |
| EVAL_THRESHOLD          | 85.0%                        | 80.0%                        |
| Pair generation         | ALL C(n,2) same-class combos | RANDOM SAMPLING per label    |
| PAIRS_PER_LABEL         | N/A                          | 50 (new config)              |
| run_inference()         | preprocess_from_path()       | cv2 + inline normalisation   |
| Terminology             | "identity"                   | "firearm"                    |

CRITICAL: why random pair sampling replaces all-combinations
-------------------------------------------------------------
The fingerprint generate_pairs() generates ALL C(n,2) positive combinations
within each identity.  This works because fingerprint identities in the
test split have ~4 images each → C(4,2) = 6 pairs per identity.

For toolmarks, after 6× augmentation, each firearm label has ~600 images
in the test split.  C(600,2) = 179,700 positive pairs per firearm ×
24 firearms = 4.3 MILLION positive pairs — completely unworkable.

Instead, this script randomly samples PAIRS_PER_LABEL positive pairs
per firearm label (default 50) and an equal number of negative pairs,
giving 2,400 total pairs.  This is:
    - Representative: covers all 24 labels equally
    - Fast: ~minutes on GPU, not hours
    - Reproducible: seeded random sampling

How evaluation works for a Siamese network
-------------------------------------------
Unlike standard classifiers, a Siamese network produces a similarity score
for a PAIR of images, not a label for a single image.  Evaluation works on pairs:

    1. Sample PAIRS_PER_LABEL same-firearm pairs  → label = 1  (MATCH)
    2. Sample equal number of diff-firearm pairs   → label = 0  (NO MATCH)
    3. Pass each pair through the model → similarity_percentage in [0, 100]
    4. Threshold: similarity >= EVAL_THRESHOLD → predicted MATCH (1), else NO MATCH (0)
    5. Compare predictions vs labels → compute all metrics

The test split (toolmark/processed_clean/test) is:
    - Never seen during training or validation
    - NOT augmented (clean evaluation signal — raw preprocessed PNGs)
    - Produced by the train_toolmark.py split_toolmark_data() function

Output files (saved to RESULTS_DIR)
-------------------------------------
    metrics_summary.txt         — all numeric metrics printed to a text file
    roc_curve.png               — ROC curve with AUC and EER annotated
    confusion_matrix.png        — confusion matrix at EVAL_THRESHOLD
    similarity_distribution.png — histogram of same- vs diff-firearm pair scores
    threshold_sweep.csv         — metrics at every threshold (for report table)

HOW TO RUN
----------
    # From project root after training:
    python -m ai_engine.training.evaluate_toolmark

    # On Colab after training:
    !python -m ai_engine.training.evaluate_toolmark
"""

import csv
import random
import sys
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from tqdm.auto import tqdm

# Add project root to path when running as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_engine.models.siamese_toolmark_network import SiameseToolmarkNetwork
from ai_engine.training.metrics_toolmark import (
    compute_metrics,
    compute_roc,
    compute_eer,
    sweep_thresholds,
    plot_roc,
    plot_confusion_matrix,
    plot_similarity_distribution,
)


# ===========================================================================
# CONFIG — all evaluation parameters in one place
# ===========================================================================

TEST_DIR     = Path("ai_engine/datasets/toolmark/processed_clean/test")
WEIGHTS_PATH = Path("ai_engine/models/weights/toolmark/best_model_toolmark.pth")
RESULTS_DIR  = Path("docs/Experiment_Results/toolmark")

EMBEDDING_DIM  = 128     # must match training config (ToolmarkCNN default)

# Primary decision threshold — confusion matrix and classification metrics
# are computed at this value.  Tune via experiments/threshold_experiment.py.
EVAL_THRESHOLD = 80.0

# Number of positive pairs sampled per firearm label.
# With 24 labels: 50 × 24 = 1,200 positive pairs + 1,200 negative pairs = 2,400 total.
# Increasing to 100 gives 4,800 pairs — still fast, more statistically robust.
PAIRS_PER_LABEL = 200

SEED    = 42
DEVICE  = torch.device("cuda" if torch.cuda.is_available() else "cpu")

VALID_EXTS = {".bmp", ".png", ".jpg", ".jpeg"}

# ===========================================================================


# ---------------------------------------------------------------------------
# Image loading — inline (no external preprocess module dependency)
# ---------------------------------------------------------------------------

def load_image_tensor(path: Path) -> torch.Tensor:
    """
    Load one toolmark PNG and return a normalised float32 tensor.

    Pipeline (identical to SiameseToolmarkDataset.load_image()):
        1. Read as grayscale uint8  →  (H, W)
        2. Scale  [0, 255]  →  [0.0, 1.0]   via / 255.0
        3. Standardise      →  [−1.0, 1.0]  via (x − 0.5) / 0.5
        4. Tensor (1, 1, H, W)  — batch dim added for model.forward_once()

    Raises:
        ValueError if cv2 cannot read the file.
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

    if img is None:
        raise ValueError(
            f"cv2.imread returned None for: {path}\n"
            f"The file may be corrupt or the path does not exist."
        )

    img = img.astype("float32") / 255.0       # [0, 255] → [0.0, 1.0]
    img = (img - 0.5) / 0.5                   # [0.0, 1.0] → [−1.0, 1.0]
    img = torch.from_numpy(img).unsqueeze(0)   # (H, W) → (1, H, W)
    return img.unsqueeze(0)                    # (1, H, W) → (1, 1, H, W)


# ---------------------------------------------------------------------------
def load_model() -> SiameseToolmarkNetwork:
    """Load trained toolmark model weights and set to eval mode."""
    if not WEIGHTS_PATH.exists():
        raise FileNotFoundError(
            f"Weights not found at {WEIGHTS_PATH}.\n"
            f"Run train_toolmark.py first, then check WEIGHTS_PATH in this file."
        )
    model = SiameseToolmarkNetwork(embedding_dim=EMBEDDING_DIM).to(DEVICE)
    state = torch.load(WEIGHTS_PATH, map_location=DEVICE)
    model.load_state_dict(state)
    model.eval()
    print(f"Model loaded from {WEIGHTS_PATH}")
    return model


# ---------------------------------------------------------------------------
def build_test_firearm_map() -> dict:
    """
    Scan TEST_DIR and return a dict mapping firearm_label → [image_paths].

    Only labels with >= 2 images are included (need at least 2 for
    positive pair sampling).

    Returns:
        dict: { "firearmA": [Path, Path, ...], "firearmB": [...], ... }
    """
    if not TEST_DIR.exists():
        raise FileNotFoundError(
            f"Test directory not found: {TEST_DIR}\n"
            f"Run train_toolmark.py with RUN_SPLIT=True first."
        )

    firearm_map = {}
    for label_dir in sorted(TEST_DIR.iterdir()):
        if not label_dir.is_dir():
            continue
        images = [
            p for p in label_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_EXTS
        ]
        if len(images) >= 2:
            firearm_map[label_dir.name] = images
        else:
            print(
                f"  WARNING: '{label_dir.name}' has only {len(images)} image(s) "
                f"— skipping (need >= 2 for positive pairs)."
            )

    print(f"Test firearm labels : {len(firearm_map)}")
    total_imgs = sum(len(v) for v in firearm_map.values())
    print(f"Test images total   : {total_imgs:,}")
    return firearm_map


# ---------------------------------------------------------------------------
def generate_pairs(
    firearm_map: dict,
) -> Tuple[List[Tuple[Path, Path]], List[int]]:
    """
    Generate balanced positive and negative image pairs from the test set
    using RANDOM SAMPLING (not all-combinations).

    Strategy
    --------
    Positive pairs (label=1): PAIRS_PER_LABEL random pairs sampled per firearm.
        Total positive = PAIRS_PER_LABEL × n_labels.

    Negative pairs (label=0): equal count, randomly sampled cross-label.
        For each negative pair: pick two DIFFERENT firearm labels, then pick
        one random image from each.  The explicit id1 ≠ id2 guard prevents
        same-label contamination (critical with only 24 labels).

    Why NOT all-combinations (as fingerprint evaluate.py does):
        After 6× augmentation, each firearm test split has ~100+ images.
        C(100,2) = 4,950 per label × 24 labels = 118,800 positive pairs —
        too slow and unbalanced vs negatives.  Random sampling gives
        representative, fast, and reproducible evaluation.

    Returns:
        pairs  : list of (Path, Path) tuples
        labels : list of 1 (same firearm) or 0 (different firearm)
    """
    rng = random.Random(SEED)

    label_names = list(firearm_map.keys())
    pos_pairs   = []
    neg_pairs   = []

    # --- Positive pairs: PAIRS_PER_LABEL per label ---
    for label, images in firearm_map.items():
        for _ in range(PAIRS_PER_LABEL):
            # random.sample guarantees two different images
            img1, img2 = rng.sample(images, 2)
            pos_pairs.append((img1, img2))

    # --- Negative pairs: equal count, cross-label ---
    n_neg = len(pos_pairs)
    attempts     = 0
    max_attempts = n_neg * 20   # generous budget; with 24 labels this is trivial

    while len(neg_pairs) < n_neg and attempts < max_attempts:
        # Explicit guard: id1 ≠ id2 — essential with only 24 labels
        id1, id2 = rng.sample(label_names, 2)   # sample() guarantees distinct
        img1 = rng.choice(firearm_map[id1])
        img2 = rng.choice(firearm_map[id2])
        neg_pairs.append((img1, img2))
        attempts += 1

    if len(neg_pairs) < n_neg:
        print(
            f"  WARNING: could only generate {len(neg_pairs)} negative pairs "
            f"(target {n_neg}) after {max_attempts} attempts."
        )

    # Combine and shuffle together so pairs are not ordered by label
    pairs  = pos_pairs + neg_pairs
    labels = [1] * len(pos_pairs) + [0] * len(neg_pairs)

    combined = list(zip(pairs, labels))
    rng.shuffle(combined)
    pairs, labels = zip(*combined)

    print(f"Positive pairs      : {len(pos_pairs):,}  "
          f"({PAIRS_PER_LABEL} per label × {len(label_names)} labels)")
    print(f"Negative pairs      : {len(neg_pairs):,}  (balanced)")
    print(f"Total pairs         : {len(pairs):,}")

    return list(pairs), list(labels)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def run_inference(
    model: SiameseToolmarkNetwork,
    pairs: List[Tuple[Path, Path]],
    batch_size: int = 64,
) -> np.ndarray:
    """
    Batched GPU inference for Siamese evaluation.

    Why this is MUCH faster
    -----------------------
    Old version:
        1 pair  -> GPU
        1 pair  -> GPU
        1 pair  -> GPU

    New version:
        64 pairs -> GPU at once

    This massively improves GPU utilisation and reduces:
        - CUDA launch overhead
        - CPU→GPU transfer overhead
        - Python loop overhead

    Returns:
        np.ndarray of similarity percentages in [0, 100].
    """
    similarities = []

    model.eval()

    with torch.no_grad():

        for start_idx in tqdm(
            range(0, len(pairs), batch_size),
            desc="Evaluating batches",
            unit="batch",
        ):

            batch_pairs = pairs[start_idx : start_idx + batch_size]

            # ----------------------------------------------------------
            # Load entire batch on CPU first
            # ----------------------------------------------------------
            batch1 = []
            batch2 = []

            for path1, path2 in batch_pairs:

                img1 = load_image_tensor(path1).squeeze(0)
                img2 = load_image_tensor(path2).squeeze(0)

                batch1.append(img1)
                batch2.append(img2)

            # ----------------------------------------------------------
            # Stack into tensors
            # Shape:
            #   (B, 1, H, W)
            # ----------------------------------------------------------
            batch1 = torch.stack(batch1).to(DEVICE, non_blocking=True)
            batch2 = torch.stack(batch2).to(DEVICE, non_blocking=True)

            # ----------------------------------------------------------
            # Forward pass on FULL BATCH
            # ----------------------------------------------------------
            emb1 = model.forward_once(batch1)
            emb2 = model.forward_once(batch2)

            # ----------------------------------------------------------
            # Vectorized similarity computation
            # ----------------------------------------------------------
            distances = F.pairwise_distance(emb1, emb2)

            sims = (1.0 - distances / 2.0) * 100.0
            sims = torch.clamp(sims, min=0.0, max=100.0)

            similarities.extend(sims.cpu().numpy())

    return np.array(similarities, dtype=float)


# ---------------------------------------------------------------------------
def save_metrics_summary(
    metrics:       dict,
    auc:           float,
    eer:           float,
    eer_threshold: float,
    threshold:     float,
    n_pairs:       int,
) -> None:
    """Print and save a human-readable metrics summary to metrics_summary.txt."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = RESULTS_DIR / "metrics_summary.txt"

    lines = [
        "=" * 58,
        "  ForensicEdge — Toolmark Evaluation Results",
        "=" * 58,
        f"  Test pairs evaluated  : {n_pairs:,}",
        f"  Decision threshold    : {threshold}%",
        f"  Weights               : {WEIGHTS_PATH}",
        "-" * 58,
        f"  Classification Metrics  (threshold = {threshold:.1f}%)",
        "-" * 58,
        f"  Accuracy   : {metrics['accuracy']  * 100:.2f}%",
        f"  Precision  : {metrics['precision'] * 100:.2f}%",
        f"  Recall     : {metrics['recall']    * 100:.2f}%",
        f"  F1 Score   : {metrics['f1']        * 100:.2f}%",
        "-" * 58,
        "  Forensic Metrics",
        "-" * 58,
        f"  FMR  (False Match Rate)     : {metrics['fmr']  * 100:.2f}%",
        f"  FNMR (False Non-Match Rate) : {metrics['fnmr'] * 100:.2f}%",
        f"  AUC                         : {auc:.4f}",
        f"  EER  (Equal Error Rate)     : {eer * 100:.2f}%",
        f"  EER Threshold               : {eer_threshold:.1f}%",
        "-" * 58,
        "  Confusion Matrix",
        "-" * 58,
        f"  TP (Correct Match)        : {metrics['tp']:,}",
        f"  TN (Correct Reject)       : {metrics['tn']:,}",
        f"  FP (False Match)          : {metrics['fp']:,}",
        f"  FN (False Non-Match)      : {metrics['fn']:,}",
        "=" * 58,
    ]

    text = "\n".join(lines)
    print("\n" + text)

    with open(save_path, "w") as f:
        f.write(text + "\n")
    print(f"\n  Summary saved → {save_path}")


# ---------------------------------------------------------------------------
def save_threshold_sweep_csv(sweep_results: List[dict]) -> None:
    """
    Save per-threshold metrics to a CSV file for the report results table
    and for experiments/threshold_experiment.py.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = RESULTS_DIR / "threshold_sweep.csv"

    fieldnames = [
        "threshold", "accuracy", "precision", "recall",
        "f1", "fmr", "fnmr", "tp", "tn", "fp", "fn",
    ]

    with open(save_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sweep_results:
            writer.writerow({k: row[k] for k in fieldnames})

    print(f"  Threshold sweep saved → {save_path}")


# ===========================================================================
# Main
# ===========================================================================
def main():
    random.seed(SEED)
    np.random.seed(SEED)

    print("=" * 58)
    print("  ForensicEdge — Toolmark Model Evaluation")
    print("=" * 58)
    print(f"  Device          : {DEVICE}")
    print(f"  Test dir        : {TEST_DIR}")
    print(f"  Threshold       : {EVAL_THRESHOLD}%")
    print(f"  Pairs per label : {PAIRS_PER_LABEL}")
    print()

    # 1. Load model
    model = load_model()

    # 2. Build test firearm label map
    print()
    firearm_map = build_test_firearm_map()

    # 3. Generate pairs (random sampling — not all combinations)
    print()
    pairs, labels = generate_pairs(firearm_map)
    labels_arr = np.array(labels, dtype=int)

    # 4. Run inference → similarity scores
    print()
    similarities = run_inference(model, pairs)

    # 5. Threshold → binary predictions
    predictions = (similarities >= EVAL_THRESHOLD).astype(int)

    # 6. Compute all metrics
    metrics                            = compute_metrics(labels_arr, predictions)
    fmr_arr, tmr_arr, thresh_arr, auc = compute_roc(labels_arr, similarities)
    eer, eer_threshold                 = compute_eer(labels_arr, similarities)
    sweep_results                      = sweep_thresholds(labels_arr, similarities)

    # 7. Save text summary
    save_metrics_summary(
        metrics       = metrics,
        auc           = auc,
        eer           = eer,
        eer_threshold = eer_threshold,
        threshold     = EVAL_THRESHOLD,
        n_pairs       = len(pairs),
    )

    # 8. Save plots
    print()
    print("  Saving plots ...")

    plot_roc(
        fmr_values = fmr_arr,
        tmr_values = tmr_arr,
        auc        = auc,
        eer        = eer,
        save_path  = RESULTS_DIR / "roc_curve.png",
    )

    plot_confusion_matrix(
        tp        = metrics["tp"],
        tn        = metrics["tn"],
        fp        = metrics["fp"],
        fn        = metrics["fn"],
        threshold = EVAL_THRESHOLD,
        save_path = RESULTS_DIR / "confusion_matrix.png",
    )

    plot_similarity_distribution(
        similarities = similarities,
        labels       = labels_arr,
        threshold    = EVAL_THRESHOLD,
        save_path    = RESULTS_DIR / "similarity_distribution.png",
    )

    # 9. Save threshold sweep CSV
    save_threshold_sweep_csv(sweep_results)

    print()
    print("=" * 58)
    print(f"  Evaluation complete. Results in: {RESULTS_DIR}")
    print("=" * 58)


if __name__ == "__main__":
    main()