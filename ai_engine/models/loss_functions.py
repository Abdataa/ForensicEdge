import os

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# ContrastiveLoss
# ---------------------------------------------------------------------------
class ContrastiveLoss(nn.Module):
    """
    Contrastive loss for Siamese network training.
    (Hadsell, Chopra & LeCun, 2006 — "Dimensionality Reduction by Learning
    an Invariant Mapping", CVPR 2006)

    Formula
    -------
        L = 0.5 * mean( y · d²  +  (1 − y) · max(0, m − d)² )

    where:
        d  = Euclidean distance between the two embeddings
        y  = 1  if the pair is the SAME identity  (positive pair)
        y  = 0  if the pair is a DIFFERENT identity (negative pair)
        m  = margin  (minimum required separation for negative pairs)

    Label convention
    ----------------
        label = 1  →  same identity  →  loss pulls distance toward 0
        label = 0  →  different      →  loss pushes distance beyond margin

    This matches SiameseFingerprintDataset which returns:
        torch.tensor(1.0, dtype=torch.float32)  for positive pairs
        torch.tensor(0.0, dtype=torch.float32)  for negative pairs

    Margin selection for L2-normalised embeddings
    ---------------------------------------------
    FingerprintCNN applies F.normalize(p=2) to every output, placing all
    embeddings on the unit hypersphere.  For unit-norm vectors:

        Minimum Euclidean distance = 0.0  (identical embeddings)
        Maximum Euclidean distance = 2.0  (opposite poles on the sphere)

    Therefore margin MUST be in (0, 2).  The default margin=1.0 is the
    midpoint — negative pairs are pushed to at least half the maximum
    possible separation.

    Setting margin=2.0 (a common mistake) means negative pairs can NEVER
    satisfy the constraint (max distance IS 2.0), so the hinge term always
    produces non-zero loss and training never converges.

    The 0.5 coefficient
    -------------------
    Without the 0.5 factor, the gradient of the same-pair term (2d) is
    approximately twice as large as the different-pair gradient (-2*hinge)
    early in training when embeddings are close together.  This imbalance
    causes the model to collapse all embeddings toward zero before it learns
    to separate identities.  The 0.5 restores the balance described in the
    original paper.

    Parameters
    ----------
    margin : float
        Minimum Euclidean distance enforced between negative pairs.
        Must be in (0, 2) for L2-normalised embeddings.
        Default 1.0.  Tune via experiments/threshold_experiment.py.
    """

    def __init__(self, margin: float = 1.0):
        super().__init__()

        if not (0.0 < margin < 2.0):
            raise ValueError(
                f"margin must be in (0, 2) for L2-normalised embeddings. "
                f"Got margin={margin}.  The maximum Euclidean distance "
                f"between two unit vectors is 2.0, so margin=2.0 can never "
                f"be satisfied and training will not converge."
            )

        self.margin = margin

    # ------------------------------------------------------------------
    def forward(
        self,
        emb1:  torch.Tensor,
        emb2:  torch.Tensor,
        label: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute contrastive loss for a batch of embedding pairs.

        Args:
            emb1  : (B, embedding_dim) float32, L2-normalised.
            emb2  : (B, embedding_dim) float32, L2-normalised.
            label : (B,) float32.  1.0 = same identity, 0.0 = different.

        Returns:
            Scalar loss tensor (differentiable — backprop works normally).
        """
        # Defensive cast — correct even if caller passes an integer tensor
        label = label.float()

        # Optional norm validation — catches accidental use of raw CNN outputs.
        # Enable by setting environment variable:  DEBUG_LOSS=1 python train.py
        if os.getenv("DEBUG_LOSS"):
            norms1 = torch.norm(emb1, p=2, dim=1)
            norms2 = torch.norm(emb2, p=2, dim=1)
            ones   = torch.ones_like(norms1)
            assert torch.allclose(norms1, ones, atol=1e-4), (
                f"emb1 is not L2-normalised (norms: {norms1[:4].tolist()}). "
                f"Ensure FingerprintCNN output is used, not raw conv features."
            )
            assert torch.allclose(norms2, ones, atol=1e-4), (
                f"emb2 is not L2-normalised (norms: {norms2[:4].tolist()}). "
                f"Ensure FingerprintCNN output is used, not raw conv features."
            )

        # Euclidean distance between each embedding pair — shape: (B,)
        distance = F.pairwise_distance(emb1, emb2, p=2)

        # Same-pair term (label=1)
        # Pulls matching embeddings toward distance = 0
        same_pair_loss = label * torch.pow(distance, 2)

        # Different-pair term (label=0)
        # Pushes non-matching embeddings beyond the margin
        # Zero penalty when distance >= margin (pair is already well-separated)
        hinge               = torch.clamp(self.margin - distance, min=0.0)
        different_pair_loss = (1.0 - label) * torch.pow(hinge, 2)

        # 0.5 coefficient from Hadsell et al. 2006
        # Balances gradient magnitudes of the same-pair and different-pair terms
        loss = 0.5 * torch.mean(same_pair_loss + different_pair_loss)

        return loss


# ---------------------------------------------------------------------------
# Quick smoke-test  (run:  python loss_functions.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    loss_fn = ContrastiveLoss(margin=1.0)

    # Simulate a batch of 4 pairs with unit-norm embeddings
    torch.manual_seed(42)
    emb1 = F.normalize(torch.randn(4, 256), p=2, dim=1)
    emb2 = F.normalize(torch.randn(4, 256), p=2, dim=1)

    labels = torch.tensor([1.0, 0.0, 1.0, 0.0])   # 2 positive, 2 negative

    loss = loss_fn(emb1, emb2, labels)

    print(f"Contrastive loss      : {loss.item():.6f}")
    print(f"Margin                : {loss_fn.margin}")
    print(f"emb1 norms (all ~1.0): {[round(n, 5) for n in torch.norm(emb1, p=2, dim=1).tolist()]}")
    print(f"emb2 norms (all ~1.0): {[round(n, 5) for n in torch.norm(emb2, p=2, dim=1).tolist()]}")

    # Verify margin validation catches the common margin=2.0 mistake
    try:
        ContrastiveLoss(margin=2.0)
    except ValueError as e:
        print(f"\nMargin guard caught   : {e}")

    print("\nSmoke-test passed.")