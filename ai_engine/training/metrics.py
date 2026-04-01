"""
ai_engine/training/metrics.py
------------------------------
Pure metric computation functions for evaluating the ForensicEdge
Siamese network on the test set.

Metrics implemented
-------------------
All metrics explicitly required by the project report:
    - Accuracy
    - Precision
    - Recall  (True Match Rate)
    - False Match Rate  (FMR)   — forensic standard term for False Positive Rate
    - False Non-Match Rate (FNMR) — forensic standard term for False Negative Rate
    - F1 Score

Additional metrics standard for biometric / similarity systems:
    - ROC curve + AUC
    - EER  (Equal Error Rate — threshold where FMR == FNMR)
    - Confusion matrix
    - Per-threshold metric sweep (used by threshold_experiment.py)

Forensic terminology mapping
-----------------------------
    Standard ML term          Forensic / biometric term
    ─────────────────────     ─────────────────────────────────────────
    True Positive  (TP)   →   Correct match   (same identity, predicted MATCH)
    True Negative  (TN)   →   Correct reject  (diff identity, predicted NO MATCH)
    False Positive (FP)   →   False Match     (diff identity, predicted MATCH)
    False Negative (FN)   →   False Non-Match (same identity, predicted NO MATCH)
    False Positive Rate   →   False Match Rate        (FMR)
    False Negative Rate   →   False Non-Match Rate    (FNMR)
    EER                   →   Threshold where FMR == FNMR — key forensic benchmark

Design
------
All functions are pure (no side effects, no global state).
evaluate.py calls these functions and handles I/O (saving plots, printing).
This separation makes metrics independently testable.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------

def compute_metrics(
    labels:      np.ndarray,
    predictions: np.ndarray,
) -> Dict[str, float]:
    """
    Compute all classification metrics from binary labels and predictions.

    Args:
        labels      : ground-truth array, 1 = same identity, 0 = different.
                      Shape (N,), dtype int or bool.
        predictions : predicted array, 1 = MATCH,  0 = NO MATCH.
                      Shape (N,), dtype int or bool.
                      Produced by thresholding similarity_percentage >= threshold.

    Returns:
        dict with keys:
            accuracy   : (TP + TN) / N
            precision  : TP / (TP + FP)  — of all predicted matches, how many correct?
            recall     : TP / (TP + FN)  — of all true matches, how many found?
            f1         : harmonic mean of precision and recall
            fmr        : FP / (FP + TN)  — False Match Rate (forensic term)
            fnmr       : FN / (FN + TP)  — False Non-Match Rate (forensic term)
            tp, tn, fp, fn : raw counts
    """
    labels      = np.asarray(labels,      dtype=int)
    predictions = np.asarray(predictions, dtype=int)

    tp = int(np.sum((predictions == 1) & (labels == 1)))
    tn = int(np.sum((predictions == 0) & (labels == 0)))
    fp = int(np.sum((predictions == 1) & (labels == 0)))
    fn = int(np.sum((predictions == 0) & (labels == 1)))

    n = len(labels)

    accuracy  = (tp + tn) / n if n > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )
    fmr  = fp / (fp + tn) if (fp + tn) > 0 else 0.0   # False Match Rate
    fnmr = fn / (fn + tp) if (fn + tp) > 0 else 0.0   # False Non-Match Rate

    return {
        "accuracy":  round(accuracy,  4),
        "precision": round(precision, 4),
        "recall":    round(recall,    4),
        "f1":        round(f1,        4),
        "fmr":       round(fmr,       4),
        "fnmr":      round(fnmr,      4),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
    }


# ---------------------------------------------------------------------------

def compute_roc(
    labels:       np.ndarray,
    similarities: np.ndarray,
    n_thresholds: int = 200,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Compute ROC curve and AUC for a range of similarity thresholds.

    Args:
        labels       : ground-truth, 1 = same identity. Shape (N,).
        similarities : predicted similarity percentages [0, 100]. Shape (N,).
        n_thresholds : number of threshold steps to sweep (default 200).

    Returns:
        fmr_values   : False Match Rate at each threshold. Shape (n_thresholds,).
        tmr_values   : True Match Rate  at each threshold. Shape (n_thresholds,).
                       (TMR = Recall = 1 − FNMR, used as y-axis on ROC)
        thresholds   : threshold values swept. Shape (n_thresholds,).
        auc          : Area Under the ROC Curve [0, 1]. Higher is better.
    """
    labels       = np.asarray(labels,       dtype=int)
    similarities = np.asarray(similarities, dtype=float)

    thresholds = np.linspace(0.0, 100.0, n_thresholds)
    fmr_values = np.zeros(n_thresholds)
    tmr_values = np.zeros(n_thresholds)

    for i, thresh in enumerate(thresholds):
        preds = (similarities >= thresh).astype(int)
        m = compute_metrics(labels, preds)
        fmr_values[i] = m["fmr"]
        tmr_values[i] = m["recall"]   # TMR = Recall = 1 - FNMR

    # AUC via trapezoidal rule (FMR on x-axis, TMR on y-axis)
    # Sort by FMR ascending for correct integration
    sort_idx = np.argsort(fmr_values)
    auc = float(np.trapz(
        tmr_values[sort_idx],
        fmr_values[sort_idx],
    ))

    return fmr_values, tmr_values, thresholds, round(abs(auc), 4)


# ---------------------------------------------------------------------------

def compute_eer(
    labels:       np.ndarray,
    similarities: np.ndarray,
    n_thresholds: int = 200,
) -> Tuple[float, float]:
    """
    Compute the Equal Error Rate (EER) — the threshold where FMR == FNMR.

    EER is the primary forensic benchmark for biometric systems.
    Lower EER → better system.

    Args:
        labels       : ground-truth, 1 = same identity. Shape (N,).
        similarities : predicted similarity percentages [0, 100]. Shape (N,).
        n_thresholds : number of thresholds to sweep.

    Returns:
        eer           : Equal Error Rate value [0, 1].
        eer_threshold : similarity threshold (%) at which EER occurs.
    """
    labels       = np.asarray(labels,       dtype=int)
    similarities = np.asarray(similarities, dtype=float)

    thresholds = np.linspace(0.0, 100.0, n_thresholds)
    fmr_values  = np.zeros(n_thresholds)
    fnmr_values = np.zeros(n_thresholds)

    for i, thresh in enumerate(thresholds):
        preds = (similarities >= thresh).astype(int)
        m = compute_metrics(labels, preds)
        fmr_values[i]  = m["fmr"]
        fnmr_values[i] = m["fnmr"]

    # EER is at the crossing point of FMR and FNMR curves
    diff = np.abs(fmr_values - fnmr_values)
    eer_idx = int(np.argmin(diff))

    eer           = float((fmr_values[eer_idx] + fnmr_values[eer_idx]) / 2)
    eer_threshold = float(thresholds[eer_idx])

    return round(eer, 4), round(eer_threshold, 2)


# ---------------------------------------------------------------------------

def sweep_thresholds(
    labels:       np.ndarray,
    similarities: np.ndarray,
    thresholds:   List[float] = None,
) -> List[Dict]:
    """
    Compute all metrics at each threshold value.
    Used by experiments/threshold_experiment.py to find the optimal threshold.

    Args:
        labels       : ground-truth. Shape (N,).
        similarities : predicted similarity percentages. Shape (N,).
        thresholds   : list of threshold values to evaluate.
                       Defaults to [50, 55, 60, 65, 70, 75, 80, 85, 90, 95].

    Returns:
        List of dicts, one per threshold, each containing:
            threshold + all keys from compute_metrics().
    """
    if thresholds is None:
        thresholds = [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0]

    results = []
    for thresh in thresholds:
        preds = (np.asarray(similarities) >= thresh).astype(int)
        m = compute_metrics(labels, preds)
        m["threshold"] = thresh
        results.append(m)

    return results


# ---------------------------------------------------------------------------
# Plotting functions
# ---------------------------------------------------------------------------

def plot_roc(
    fmr_values: np.ndarray,
    tmr_values: np.ndarray,
    auc:        float,
    eer:        float,
    save_path:  str | Path = None,
) -> None:
    """
    Plot the ROC curve (FMR vs TMR) with AUC and EER annotations.

    Args:
        fmr_values : False Match Rate array from compute_roc().
        tmr_values : True Match Rate array from compute_roc().
        auc        : AUC value from compute_roc().
        eer        : EER value from compute_eer().
        save_path  : if provided, saves the figure to this path.
                     If None, calls plt.show() instead.
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 6))

    ax.plot(fmr_values, tmr_values, color="#1a6faf", linewidth=2,
            label=f"ROC curve  (AUC = {auc:.4f})")
    ax.plot([0, 1], [0, 1], color="#999999", linestyle="--",
            linewidth=1, label="Random classifier")

    # Mark EER point
    ax.scatter([eer], [1 - eer], color="#d94f3d", zorder=5,
               label=f"EER = {eer:.4f}")
    ax.annotate(
        f"EER = {eer:.4f}",
        xy=(eer, 1 - eer),
        xytext=(eer + 0.05, 1 - eer - 0.08),
        fontsize=9,
        color="#d94f3d",
        arrowprops=dict(arrowstyle="->", color="#d94f3d"),
    )

    ax.set_xlabel("False Match Rate (FMR)", fontsize=11)
    ax.set_ylabel("True Match Rate (TMR = Recall)", fontsize=11)
    ax.set_title("ForensicEdge — ROC Curve", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150)
        print(f"  ROC curve saved → {save_path}")
        plt.close()
    else:
        plt.show()


# ---------------------------------------------------------------------------

def plot_confusion_matrix(
    tp: int, tn: int, fp: int, fn: int,
    threshold:  float,
    save_path:  str | Path = None,
) -> None:
    """
    Plot the confusion matrix at a given threshold.

    Args:
        tp, tn, fp, fn : counts from compute_metrics().
        threshold      : the similarity threshold used (shown in title).
        save_path      : if provided, saves figure. If None, calls plt.show().
    """
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    matrix = np.array([[tn, fp], [fn, tp]])
    labels_text = np.array([
        [f"TN\n{tn}", f"FP\n{fp}"],
        [f"FN\n{fn}", f"TP\n{tp}"],
    ])

    fig, ax = plt.subplots(figsize=(5, 4))

    cmap = plt.cm.Blues
    im = ax.imshow(matrix, interpolation="nearest", cmap=cmap)
    plt.colorbar(im, ax=ax)

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Predicted\nNO MATCH", "Predicted\nMATCH"], fontsize=10)
    ax.set_yticklabels(["Actual\nDIFFERENT", "Actual\nSAME"], fontsize=10)

    thresh_color = matrix.max() / 2.0
    for i in range(2):
        for j in range(2):
            ax.text(
                j, i, labels_text[i, j],
                ha="center", va="center", fontsize=12,
                color="white" if matrix[i, j] > thresh_color else "black",
            )

    ax.set_title(
        f"ForensicEdge — Confusion Matrix\n(threshold = {threshold}%)",
        fontsize=12, fontweight="bold",
    )
    ax.set_xlabel("Predicted label", fontsize=11)
    ax.set_ylabel("True label", fontsize=11)

    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150)
        print(f"  Confusion matrix saved → {save_path}")
        plt.close()
    else:
        plt.show()


# ---------------------------------------------------------------------------

def plot_similarity_distribution(
    similarities: np.ndarray,
    labels:       np.ndarray,
    threshold:    float,
    save_path:    str | Path = None,
) -> None:
    """
    Plot similarity score distributions for positive and negative pairs.

    Shows two overlapping histograms:
        - Blue  : same-identity pairs  (should cluster near 100%)
        - Red   : diff-identity pairs  (should cluster near 0%)
        - Dashed vertical line at the decision threshold

    A well-trained model shows clear separation between the two distributions.
    Overlap region = classification errors.

    Args:
        similarities : similarity percentages [0, 100]. Shape (N,).
        labels       : 1 = same identity, 0 = different. Shape (N,).
        threshold    : decision threshold (drawn as vertical line).
        save_path    : if provided, saves figure.
    """
    import matplotlib.pyplot as plt

    pos_sims = similarities[labels == 1]
    neg_sims = similarities[labels == 0]

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.hist(pos_sims, bins=50, alpha=0.6, color="#1a6faf",
            label=f"Same identity  (n={len(pos_sims):,})", density=True)
    ax.hist(neg_sims, bins=50, alpha=0.6, color="#d94f3d",
            label=f"Diff identity  (n={len(neg_sims):,})", density=True)

    ax.axvline(x=threshold, color="#333333", linestyle="--", linewidth=1.5,
               label=f"Threshold = {threshold}%")

    ax.set_xlabel("Similarity Percentage (%)", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title("ForensicEdge — Similarity Score Distribution", fontsize=13,
                 fontweight="bold")
    ax.legend(fontsize=10)
    ax.set_xlim([0, 100])
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150)
        print(f"  Distribution plot saved → {save_path}")
        plt.close()
    else:
        plt.show()