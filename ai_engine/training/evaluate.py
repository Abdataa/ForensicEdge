"""
ai_engine/training/evaluate.py
--------------------------------
Evaluates the trained ForensicEdge Siamese network on the held-out test set
and produces all metrics required by the project report:

    Accuracy, Precision, Recall, False Match Rate (FMR),
    False Non-Match Rate (FNMR), F1, AUC, EER,
    Confusion Matrix, ROC Curve, Similarity Distribution plot.

How evaluation works for a Siamese network
-------------------------------------------
Unlike standard classifiers, a Siamese network produces a similarity score
for a PAIR of images, not a label for a single image.  Evaluation therefore
works on pairs:

    1. Generate all same-identity pairs  → label = 1  (MATCH)
    2. Sample equal number of diff-identity pairs → label = 0  (NO MATCH)
    3. Pass each pair through the model → similarity_percentage in [0, 100]
    4. Threshold: similarity >= THRESHOLD → predicted MATCH (1), else NO MATCH (0)
    5. Compare predictions vs labels → compute all metrics

Pair generation uses the test split (processed_clean/test) which:
    - Was never seen during training or validation
    - Is NOT augmented (clean evaluation signal)
    - Uses the same preprocessing as inference (via inference/preprocess.py)

Output files (saved to RESULTS_DIR)
-------------------------------------
    metrics_summary.txt        — all numeric metrics printed to a text file
    roc_curve.png              — ROC curve with AUC and EER annotated
    confusion_matrix.png       — confusion matrix at EVAL_THRESHOLD
    similarity_distribution.png— histogram of positive vs negative pair scores
    threshold_sweep.csv        — metrics at every threshold (for report table)

HOW TO RUN
----------
    # From project root after training:
    python -m ai_engine.training.evaluate

    # On Colab after training:
    !python -m ai_engine.training.evaluate
"""

import sys
import csv
import random
import itertools
from pathlib import Path
from typing  import List, Tuple

import torch
import numpy as np
from tqdm.auto import tqdm

# Add project root to path when running as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_engine.inference.preprocess  import preprocess_from_path
from ai_engine.models.siamese_network import SiameseNetwork
from ai_engine.training.metrics import (
    compute_metrics,
    compute_roc,
    compute_eer,
    sweep_thresholds,
    plot_roc,
    plot_confusion_matrix,
    plot_similarity_distribution,
)


# ===========================================================================
# CONFIG
# ===========================================================================

TEST_DIR     = Path("ai_engine/datasets/processed_clean/test")
WEIGHTS_PATH = Path("ai_engine/models/weights/best_model.pth")
RESULTS_DIR  = Path("docs/Experiment_Results")

EMBEDDING_DIM    = 256      # must match training config
EVAL_THRESHOLD   = 85.0     # primary threshold for confusion matrix / metrics
                             # tune via experiments/threshold_experiment.py
MAX_PAIRS        = 20_000   # cap total pairs to control evaluation time
                             # set to None to use all pairs (may be slow)
SEED             = 42
DEVICE           = torch.device("cuda" if torch.cuda.is_available() else "cpu")
VALID_EXTS       = {".bmp", ".png", ".jpg", ".jpeg"}

# ===========================================================================


def load_model() -> SiameseNetwork:
    """Load trained model weights and set to eval mode."""
    if not WEIGHTS_PATH.exists():
        raise FileNotFoundError(
            f"Weights not found at {WEIGHTS_PATH}.\n"
            f"Run train_siamese.py first."
        )
    model = SiameseNetwork(embedding_dim=EMBEDDING_DIM).to(DEVICE)
    state = torch.load(WEIGHTS_PATH, map_location=DEVICE)
    model.load_state_dict(state)
    model.eval()
    print(f"Model loaded from {WEIGHTS_PATH}")
    return model


# ---------------------------------------------------------------------------
def build_test_identity_map() -> dict:
    """
    Scan TEST_DIR and return a dict mapping identity_name → [image_paths].
    Only identities with >= 2 images are included (need at least 2 for pairs).
    """
    if not TEST_DIR.exists():
        raise FileNotFoundError(f"Test directory not found: {TEST_DIR}")

    identity_map = {}
    for identity_dir in sorted(TEST_DIR.iterdir()):
        if not identity_dir.is_dir():
            continue
        images = [
            p for p in identity_dir.iterdir()
            if p.suffix.lower() in VALID_EXTS
        ]
        if len(images) >= 2:
            identity_map[identity_dir.name] = images

    print(f"Test identities: {len(identity_map)}")
    total_imgs = sum(len(v) for v in identity_map.values())
    print(f"Test images    : {total_imgs}")
    return identity_map


# ---------------------------------------------------------------------------
def generate_pairs(
    identity_map: dict,
) -> Tuple[List[Tuple[Path, Path]], List[int]]:
    """
    Generate balanced positive and negative image pairs from the test set.

    Positive pairs (label=1): all C(n,2) combinations within each identity.
    Negative pairs (label=0): randomly sampled cross-identity pairs,
                              equal in count to positive pairs (balanced).

    If the total pairs exceed MAX_PAIRS, both positive and negative sets
    are randomly subsampled to MAX_PAIRS // 2 each.

    Returns:
        pairs  : list of (path1, path2) tuples
        labels : list of 1 (same) or 0 (different)
    """
    random.seed(SEED)

    identity_names = list(identity_map.keys())

    # --- Positive pairs ---
    pos_pairs = []
    for name, images in identity_map.items():
        for img1, img2 in itertools.combinations(images, 2):
            pos_pairs.append((img1, img2))

    # --- Negative pairs (sample equal count) ---
    n_neg = len(pos_pairs)
    neg_pairs = []
    attempts  = 0
    max_attempts = n_neg * 10

    while len(neg_pairs) < n_neg and attempts < max_attempts:
        id1, id2 = random.sample(identity_names, 2)
        img1 = random.choice(identity_map[id1])
        img2 = random.choice(identity_map[id2])
        neg_pairs.append((img1, img2))
        attempts += 1

    # --- Subsample if exceeding MAX_PAIRS ---
    if MAX_PAIRS is not None:
        half = MAX_PAIRS // 2
        if len(pos_pairs) > half:
            pos_pairs = random.sample(pos_pairs, half)
        if len(neg_pairs) > half:
            neg_pairs = random.sample(neg_pairs, half)

    pairs  = pos_pairs + neg_pairs
    labels = [1] * len(pos_pairs) + [0] * len(neg_pairs)

    # Shuffle together so pairs aren't ordered by label
    combined = list(zip(pairs, labels))
    random.shuffle(combined)
    pairs, labels = zip(*combined)

    print(f"Positive pairs : {len(pos_pairs):,}")
    print(f"Negative pairs : {len(neg_pairs):,}")
    print(f"Total pairs    : {len(pairs):,}")

    return list(pairs), list(labels)


# ---------------------------------------------------------------------------
def run_inference(
    model: SiameseNetwork,
    pairs: List[Tuple[Path, Path]],
) -> np.ndarray:
    """
    Run the model on all pairs and return similarity percentages.

    Args:
        model : trained SiameseNetwork in eval() mode.
        pairs : list of (path1, path2) tuples.

    Returns:
        similarities : np.ndarray of shape (N,), values in [0.0, 100.0].
    """
    similarities = []

    with torch.no_grad():
        for path1, path2 in tqdm(pairs, desc="Evaluating pairs", unit="pair"):
            # preprocess_from_path returns (1, 1, 224, 224) tensor
            t1 = preprocess_from_path(path1).to(DEVICE)
            t2 = preprocess_from_path(path2).to(DEVICE)

            emb1 = model.forward_once(t1)
            emb2 = model.forward_once(t2)

            sim = model.similarity_percentage(emb1, emb2).item()
            similarities.append(sim)

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
        "=" * 55,
        "  ForensicEdge — Evaluation Results",
        "=" * 55,
        f"  Test pairs evaluated : {n_pairs:,}",
        f"  Decision threshold   : {threshold}%",
        f"  Weights              : {WEIGHTS_PATH}",
        "-" * 55,
        "  Classification Metrics  (at threshold = {:.1f}%)".format(threshold),
        "-" * 55,
        f"  Accuracy   : {metrics['accuracy']  * 100:.2f}%",
        f"  Precision  : {metrics['precision'] * 100:.2f}%",
        f"  Recall     : {metrics['recall']    * 100:.2f}%",
        f"  F1 Score   : {metrics['f1']        * 100:.2f}%",
        "-" * 55,
        "  Forensic Metrics",
        "-" * 55,
        f"  FMR  (False Match Rate)     : {metrics['fmr']  * 100:.2f}%",
        f"  FNMR (False Non-Match Rate) : {metrics['fnmr'] * 100:.2f}%",
        f"  AUC                         : {auc:.4f}",
        f"  EER  (Equal Error Rate)     : {eer * 100:.2f}%",
        f"  EER Threshold               : {eer_threshold:.1f}%",
        "-" * 55,
        "  Confusion Matrix",
        "-" * 55,
        f"  TP (Correct Match)      : {metrics['tp']:,}",
        f"  TN (Correct Reject)     : {metrics['tn']:,}",
        f"  FP (False Match)        : {metrics['fp']:,}",
        f"  FN (False Non-Match)    : {metrics['fn']:,}",
        "=" * 55,
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

    print("=" * 55)
    print("  ForensicEdge — Model Evaluation")
    print("=" * 55)
    print(f"  Device    : {DEVICE}")
    print(f"  Test dir  : {TEST_DIR}")
    print(f"  Threshold : {EVAL_THRESHOLD}%")
    print(f"  Max pairs : {MAX_PAIRS:,}" if MAX_PAIRS else "  Max pairs : all")
    print()

    # 1. Load model
    model = load_model()

    # 2. Build test identity map
    identity_map = build_test_identity_map()

    # 3. Generate pairs
    print()
    pairs, labels = generate_pairs(identity_map)
    labels_arr = np.array(labels, dtype=int)

    # 4. Run inference → similarity scores
    print()
    similarities = run_inference(model, pairs)

    # 5. Threshold → binary predictions
    predictions = (similarities >= EVAL_THRESHOLD).astype(int)

    # 6. Compute all metrics
    metrics       = compute_metrics(labels_arr, predictions)
    fmr_arr, tmr_arr, thresh_arr, auc = compute_roc(labels_arr, similarities)
    eer, eer_threshold                 = compute_eer(labels_arr, similarities)
    sweep_results = sweep_thresholds(labels_arr, similarities)

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
        tp         = metrics["tp"],
        tn         = metrics["tn"],
        fp         = metrics["fp"],
        fn         = metrics["fn"],
        threshold  = EVAL_THRESHOLD,
        save_path  = RESULTS_DIR / "confusion_matrix.png",
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
    print("=" * 55)
    print(f"  Evaluation complete. Results in: {RESULTS_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()