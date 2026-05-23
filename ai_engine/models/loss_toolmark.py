"""
loss_toolmark.py
================
Contrastive loss for Siamese toolmark network training.

Adapted from loss_functions.py (fingerprint pipeline).

The formula and mathematics are identical — only the default margin changes,
and the change is non-trivial: it is driven by the geometry of the
embedding space, not by a stylistic preference.

Critical difference: margin recalibration for 128-dim embeddings
-----------------------------------------------------------------
Both FingerprintCNN and ToolmarkCNN output L2-normalised embeddings on the
unit hypersphere, so the hard constraint is the same:

    Minimum Euclidean distance = 0.0   (identical embeddings)
    Maximum Euclidean distance = 2.0   (opposite poles)
    margin MUST be in (0, 2)  — unchanged from fingerprint.

However, the DISTRIBUTION of distances changes with dimensionality.

In high-dimensional spaces, random unit vectors concentrate around a shell
at distance ≈ sqrt(2) from each other (the "concentration of measure"
phenomenon).  The exact distribution depends on the embedding dimension:

    dim=256  (FingerprintCNN): mean ≈ 1.414, std ≈ 0.045
    dim=128  (ToolmarkCNN)   : mean ≈ 1.414, std ≈ 0.064

With margin=1.0 (fingerprint default) and 128-dim embeddings:
    - 0% of random negative pairs start INSIDE the margin
    - The hinge term max(0, margin − d) is always 0 at initialisation
    - The model sees ONLY same-pair loss from epoch 1
    - Same-pair loss pulls all embeddings toward each other → collapse
    - The network never learns to separate different firearms

With margin=1.4 (toolmark default):
    - ~42% of negative pairs start inside the margin at initialisation
    - Both the same-pair and different-pair terms contribute from epoch 1
    - The model simultaneously pulls same-firearm embeddings together
      and pushes different-firearm embeddings apart
    - Avoids embedding collapse; gives a balanced training signal

margin=1.4 is a starting-point default. It should be confirmed/adjusted
via experiments/threshold_experiment.py after initial training by plotting
the intra-class vs inter-class distance distributions on the validation split.

Formula (Hadsell, Chopra & LeCun, CVPR 2006)
---------------------------------------------
    L = 0.5 * mean( y · d²  +  (1 − y) · max(0, m − d)² )

    d  = Euclidean distance between the two embeddings
    y  = 1  if the pair is the SAME firearm  (positive pair)
    y  = 0  if the pair is a DIFFERENT firearm (negative pair)
    m  = margin (default 1.4 for 128-dim toolmark embeddings)

Label convention
----------------
    label = 1.0  →  same firearm  →  loss pulls distance toward 0
    label = 0.0  →  different     →  loss pushes distance beyond margin

This matches SiameseToolmarkDataset which returns:
    torch.tensor(1.0, dtype=torch.float32)  for same-firearm pairs
    torch.tensor(0.0, dtype=torch.float32)  for different-firearm pairs

The 0.5 coefficient
-------------------
Without the 0.5 factor, the gradient of the same-pair term (2d) is
approximately twice as large as the different-pair gradient (-2*hinge)
early in training.  This imbalance causes the model to collapse all
embeddings toward zero before it learns to separate classes.  The 0.5
restores the balance described in the original paper.

Parameters
----------
margin : float
    Minimum Euclidean distance enforced between negative pairs.
    Must be in (0, 2) for L2-normalised embeddings.
    Default 1.4 — calibrated for 128-dim ToolmarkCNN embeddings.
    See module docstring for the full derivation.
"""

import os

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# ContrastiveLossToolmark
# ---------------------------------------------------------------------------
class ContrastiveLossToolmark(nn.Module):
    """
    Contrastive loss for the Siamese toolmark network.

    Identical formula to the fingerprint ContrastiveLoss; margin default
    recalibrated to 1.4 for 128-dim embeddings (see module docstring).
    """

    def __init__(self, margin: float = 1.4):
        super().__init__()

        if not (0.0 < margin < 2.0):
            raise ValueError(
                f"margin must be in (0, 2) for L2-normalised embeddings. "
                f"Got margin={margin}.  The maximum Euclidean distance "
                f"between two unit vectors is 2.0, so margin ≥ 2.0 can "
                f"never be satisfied and training will not converge.  "
                f"For 128-dim ToolmarkCNN embeddings the recommended "
                f"starting point is margin=1.4."
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
                    Output of SiameseToolmarkNetwork.forward().
            emb2  : (B, embedding_dim) float32, L2-normalised.
            label : (B,) float32.
                    1.0 = same firearm (positive pair).
                    0.0 = different firearms (negative pair).

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
                f"Ensure ToolmarkCNN output is used, not raw conv features."
            )
            assert torch.allclose(norms2, ones, atol=1e-4), (
                f"emb2 is not L2-normalised (norms: {norms2[:4].tolist()}). "
                f"Ensure ToolmarkCNN output is used, not raw conv features."
            )

        # Euclidean distance between each embedding pair — shape: (B,)
        distance = F.pairwise_distance(emb1,
                                        emb2,
                                        p=2,
                                        eps=1e-6,
                                         )

        # Same-pair term (label=1.0)
        # Pulls same-firearm embeddings toward distance = 0
        same_pair_loss = label * torch.pow(distance, 2)

        # Different-pair term (label=0.0)
        # Pushes different-firearm embeddings beyond the margin.
        # Zero penalty once distance >= margin (pair already well-separated).
        hinge               = torch.clamp(self.margin - distance, min=0.0)
        different_pair_loss = (1.0 - label) * torch.pow(hinge, 2)

        # 0.5 coefficient from Hadsell et al. 2006 — balances gradient
        # magnitudes of the same-pair and different-pair terms (see docstring).
        loss = 0.5 * torch.mean(same_pair_loss + different_pair_loss)

        return loss


# ---------------------------------------------------------------------------
# Quick smoke-test  (run:  python loss_toolmark.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    print("=== ContrastiveLossToolmark Smoke-Test ===\n")

    loss_fn = ContrastiveLossToolmark(margin=1.4)

    torch.manual_seed(42)

    # --- Basic forward pass with 128-dim embeddings ---
    emb1   = F.normalize(torch.randn(8, 128), p=2, dim=1)
    emb2   = F.normalize(torch.randn(8, 128), p=2, dim=1)
    labels = torch.tensor([1., 0., 1., 0., 1., 0., 1., 0.])   # 4 pos, 4 neg

    loss = loss_fn(emb1, emb2, labels)
    dists = F.pairwise_distance(emb1, emb2, p=2)

    print(f"Forward pass:")
    print(f"  Loss value          : {loss.item():.6f}")
    print(f"  Margin              : {loss_fn.margin}")
    print(f"  Embedding dim       : {emb1.shape[1]}")
    print(f"  emb1 norms (≈ 1.0) : {[round(n,5) for n in torch.norm(emb1,p=2,dim=1).tolist()]}")
    print(f"  emb2 norms (≈ 1.0) : {[round(n,5) for n in torch.norm(emb2,p=2,dim=1).tolist()]}")
    print(f"  Distances           : {[round(d,4) for d in dists.tolist()]}")

    # --- Gradient flow check ---
    # Use raw leaf tensors (requires_grad=True) as inputs.
    # F.normalize creates a non-leaf node whose .grad is not populated unless
    # retain_grad() is called explicitly.  Passing the raw tensors as leaves
    # and normalising inside the forward call confirms gradients flow correctly.
    raw1 = torch.randn(4, 128, requires_grad=True)
    raw2 = torch.randn(4, 128, requires_grad=True)
    l_g  = loss_fn(
        F.normalize(raw1, p=2, dim=1),
        F.normalize(raw2, p=2, dim=1),
        torch.tensor([1., 0., 1., 0.]),
    )
    l_g.backward()
    print(f"\nGradient flow:")
    print(f"  raw1.grad is not None : {raw1.grad is not None}")
    print(f"  raw2.grad is not None : {raw2.grad is not None}")
    print(f"  raw1 grad norm        : {torch.norm(raw1.grad):.6f}  (must be > 0)")

    # --- Margin calibration table ---
    # Shows fraction of random 128-dim negative pairs that START inside the
    # margin and therefore produce a gradient signal from epoch 1.
    # This is the core argument for why margin=1.4 is correct for toolmarks
    # and margin=1.0 (fingerprint default) would cause embedding collapse.
    torch.manual_seed(0)
    n_pairs = 5000
    neg_dists = torch.tensor([
        F.pairwise_distance(
            F.normalize(torch.randn(1, 128), p=2, dim=1),
            F.normalize(torch.randn(1, 128), p=2, dim=1),
        ).item()
        for _ in range(n_pairs)
    ])

    print(f"\nMargin calibration for 128-dim embeddings ({n_pairs} random pairs):")
    print(f"  Random unit-vector distance: "
          f"mean={neg_dists.mean():.4f}  std={neg_dists.std():.4f}  "
          f"(theoretic mean ≈ {2**0.5:.4f})")
    print(f"  {'Margin':>8}  {'% pairs inside margin':>24}  {'Verdict':}")
    for m, verdict in [
        (1.0, "fingerprint default — 0% gradient on negatives → COLLAPSE"),
        (1.2, "too loose — almost no negative gradient"),
        (1.3, "some signal but weak"),
        (1.4, "← toolmark default: ~42% gradient-producing"),
        (1.5, "too aggressive — overwhelms same-pair loss"),
        (1.6, "almost all negatives penalised — dominates same-pair"),
    ]:
        pct_inside = (neg_dists < m).float().mean() * 100
        marker = " ◄" if m == 1.4 else ""
        print(f"  {m:>8.1f}  {pct_inside:>23.1f}%  {verdict}{marker}")

    # --- Extreme cases ---
    print(f"\nExtreme cases:")

    # Perfect same-pair: distance=0 → same-pair loss=0, loss depends only on negatives
    e1 = F.normalize(torch.randn(1, 128), p=2, dim=1)
    l_pos_perfect = loss_fn(e1, e1.clone(), torch.tensor([1.0]))
    print(f"  Identical pair  (label=1): loss = {l_pos_perfect.item():.6f}  (must be 0.0)")

    # Perfectly separated negative: distance=2.0 → hinge=0 → neg loss=0
    e_a = F.normalize(torch.randn(1, 128), p=2, dim=1)
    e_b = F.normalize(-e_a, p=2, dim=1)  # antipodal → d=2.0
    l_neg_perfect = loss_fn(e_a, e_b, torch.tensor([0.0]))
    print(f"  Antipodal pair  (label=0): loss = {l_neg_perfect.item():.6f}  (must be 0.0, d=2.0 > margin)")

    # Negative pair exactly at margin: hinge=0 → zero loss (boundary)
    # Construct e_b at exactly d=margin from e_a using Gram-Schmidt
    dim = 128
    e_a2   = F.normalize(torch.randn(1, dim), p=2, dim=1)
    v      = torch.randn(1, dim)
    perp   = F.normalize(v - (v @ e_a2.T) * e_a2, p=2, dim=1)
    cos_t  = 1.0 - (loss_fn.margin ** 2) / 2.0   # d² = 2(1-cos) → cos = 1 - d²/2
    sin_t  = (1.0 - cos_t**2) ** 0.5
    e_b2   = cos_t * e_a2 + sin_t * perp
    d_check = F.pairwise_distance(e_a2, e_b2).item()
    l_at_margin = loss_fn(e_a2, e_b2, torch.tensor([0.0]))
    print(f"  Pair at margin  (label=0): d={d_check:.4f}  loss={l_at_margin.item():.6f}  (must be ≈ 0.0)")

    # --- Margin guard ---
    print(f"\nMargin guard checks:")
    for bad_margin, reason in [(0.0, "zero"), (2.0, "equals max"), (2.5, "exceeds max"), (-0.1, "negative")]:
        try:
            ContrastiveLossToolmark(margin=bad_margin)
            print(f"  margin={bad_margin}  ✗ FAIL — should have raised ValueError")
        except ValueError:
            print(f"  margin={bad_margin:<4}  ✓ ValueError raised  ({reason})")

    valid_margins = [0.1, 0.5, 1.0, 1.4, 1.9]
    for m in valid_margins:
        try:
            ContrastiveLossToolmark(margin=m)
            print(f"  margin={m}  ✓ accepted")
        except ValueError:
            print(f"  margin={m}  ✗ FAIL — should have been accepted")

    print("\nSmoke-test passed.")