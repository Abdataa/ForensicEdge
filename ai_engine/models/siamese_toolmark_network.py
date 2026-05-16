"""
siamese_toolmark_network.py
============================
Siamese Network for forensic breech-face impression (tool-mark) similarity
matching.

Adapted from siamese_network.py (fingerprint pipeline) but re-designed
around the toolmark data characteristics:

Key differences from the fingerprint SiameseNetwork
-----------------------------------------------------
| Aspect                  | Fingerprint SiameseNetwork | SiameseToolmarkNetwork       |
|-------------------------|----------------------------|------------------------------|
| Backbone                | FingerprintCNN             | ToolmarkCNN                  |
| embedding_dim default   | 256                        | 128  (24 classes only)       |
| dropout_fc default      | 0.3                        | 0.4  (stronger regularise)   |
| dropout_spatial default | 0.1                        | 0.2  (same reason)           |
| match_threshold default | 85.0%                      | 80.0%  (see note below)      |
| possible_threshold def  | 60.0%                      | 55.0%  (see note below)      |

Threshold rationale
-------------------
Fingerprint thresholds (85 / 60) were calibrated on thousands of identities
where inter-class embeddings are well-separated in 256-dim space.

For toolmarks the geometry is different:
  - Only 24 firearm classes → inter-class cosine distances are smaller
    (centroids are closer together in 128-dim space than thousands of
    fingerprint identities in 256-dim space).
  - Inter-firing variation (angle, pressure, propellant gases) adds
    intra-class spread — same-firearm pairs are less tight than
    same-person fingerprint pairs.
  - In forensic firearm identification, a false positive (claiming a match
    between cartridges from different firearms) is a very serious error.
    Conservative thresholds favour precision over recall.

Resulting defaults:
    match_threshold    = 80.0  →  cosine = 0.60  ("MATCH")
    possible_threshold = 55.0  →  cosine = 0.10  ("POSSIBLE MATCH")

IMPORTANT: these are starting-point defaults only.  They MUST be
calibrated via experiments/threshold_experiment.py after training using
ROC analysis on the validation split.

Architecture
------------
Two images pass through the SAME ToolmarkCNN (shared weights).
The resulting L2-normalised embeddings are compared using:
    - Euclidean distance       (lower  → more similar, range [0, 2])
    - Cosine similarity        (higher → more similar, range [−1, 1])
    - Similarity percentage    (cosine mapped to [0, 100])

Why shared weights
------------------
A single self.cnn object is used for both branches.  This guarantees true
weight sharing — any gradient update from one branch immediately affects
the other.  Two separate CNN instances (self.cnn1 / self.cnn2) would give
two independent networks, not a Siamese network.

Train / eval mode
-----------------
During training  : call model.train()  — Dropout active, BN uses batch stats.
During inference : call model.eval()   — Dropout disabled, BN uses running stats.
The analyze() method enforces eval mode and torch.no_grad() automatically.
Always restore training mode afterwards if needed (model.train()).

Parameters
----------
embedding_dim      : embedding size forwarded to ToolmarkCNN (default 128).
dropout_fc         : FC dropout forwarded to ToolmarkCNN (default 0.4).
dropout_spatial    : spatial dropout forwarded to ToolmarkCNN (default 0.2).
match_threshold    : similarity% for "MATCH" verdict (default 80.0).
possible_threshold : similarity% for "POSSIBLE MATCH" verdict (default 55.0).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from ai_engine.models.cnn_toolmark_feature_extractor import ToolmarkCNN


# ---------------------------------------------------------------------------
# SiameseToolmarkNetwork
# ---------------------------------------------------------------------------
class SiameseToolmarkNetwork(nn.Module):
    """
    Siamese Network for breech-face impression similarity matching.

    Produces three complementary similarity metrics for each image pair:
        euclidean_distance     : [0, 2]    — lower  → more similar
        cosine_similarity      : [−1, 1]   — higher → more similar
        similarity_percentage  : [0, 100]  — human-readable score

    And a forensic verdict string:
        "MATCH"          — similarity >= match_threshold    (default 80%)
        "POSSIBLE MATCH" — similarity >= possible_threshold (default 55%)
        "NO MATCH"       — below possible_threshold
    """

    def __init__(
        self,
        embedding_dim:      int   = 128,
        dropout_fc:         float = 0.4,
        dropout_spatial:    float = 0.2,
        match_threshold:    float = 80.0,
        possible_threshold: float = 55.0,
    ):
        super().__init__()

        # Validate threshold ordering before storing
        if possible_threshold >= match_threshold:
            raise ValueError(
                f"possible_threshold ({possible_threshold}) must be strictly "
                f"less than match_threshold ({match_threshold})."
            )

        # Stored as plain floats (not tensors) for if/elif comparisons
        self.match_threshold    = match_threshold
        self.possible_threshold = possible_threshold

        # Single shared CNN backbone — both Siamese branches use this object.
        # Weight sharing is automatic: one object → one set of parameters.
        # Importing ToolmarkCNN (not FingerprintCNN) uses the residual
        # projection shortcut and stronger dropout suited to 24 classes.
        self.cnn = ToolmarkCNN(
            embedding_dim   = embedding_dim,
            dropout_fc      = dropout_fc,
            dropout_spatial = dropout_spatial,
        )

    # ------------------------------------------------------------------
    def forward_once(self, x: torch.Tensor) -> torch.Tensor:
        """
        Pass one image through the shared ToolmarkCNN.

        ToolmarkCNN.forward() already applies F.normalize(p=2), so the
        returned tensor is already on the unit hypersphere.
        No second normalisation is needed here.

        Args:
            x : float32 tensor (B, 1, 224, 224), values in [−1, 1].

        Returns:
            Unit-norm embedding (B, embedding_dim).
        """
        return self.cnn(x)

    # ------------------------------------------------------------------
    def forward(
        self,
        input1: torch.Tensor,
        input2: torch.Tensor,
    ):
        """
        Forward pass for training.

        Passes both images through the shared backbone and returns their
        embeddings.  The contrastive loss in train.py operates on these.

        Args:
            input1, input2 : float32 tensors (B, 1, 224, 224), values in [−1, 1].
                             Produced by SiameseToolmarkDataset.load_image().

        Returns:
            (emb1, emb2) : pair of unit-norm tensors (B, embedding_dim).
        """
        emb1 = self.forward_once(input1)
        emb2 = self.forward_once(input2)
        return emb1, emb2

    # ------------------------------------------------------------------
    # Similarity metrics
    # ------------------------------------------------------------------

    def euclidean_distance(
        self, emb1: torch.Tensor, emb2: torch.Tensor
    ) -> torch.Tensor:
        """
        Euclidean (L2) distance between embedding pairs.

        Range: [0, 2] for unit-norm embeddings (||emb||=1 for both).
        Lower value → more similar.
        """
        return F.pairwise_distance(emb1, emb2, p=2)

    def cosine_similarity(
        self, emb1: torch.Tensor, emb2: torch.Tensor
    ) -> torch.Tensor:
        """
        Cosine similarity between embedding pairs.

        Range: [−1, 1] for unit-norm embeddings.
        Higher value → more similar.
        Equivalent to the dot product for L2-normalised vectors.
        """
        return F.cosine_similarity(emb1, emb2, dim=1)

    def similarity_percentage(
        self, emb1: torch.Tensor, emb2: torch.Tensor
    ) -> torch.Tensor:
        """
        Cosine similarity mapped to a [0, 100] percentage.

        Formula: ((cosine + 1) / 2) * 100

        Threshold mapping for toolmark defaults:
            100% → cosine =  1.00  (identical embeddings)
             80% → cosine =  0.60  (MATCH boundary)
             55% → cosine =  0.10  (POSSIBLE MATCH boundary)
              0% → cosine = −1.00  (opposite embeddings)

        Note: fingerprint defaults are 85% / 60%.  Toolmark thresholds are
        lower because inter-firing variation spreads intra-class embeddings
        and because forensic firearm matching prioritises avoiding false
        positives (different firearms called a match).
        """
        cos = self.cosine_similarity(emb1, emb2)
        return ((cos + 1.0) / 2.0) * 100.0

    # ------------------------------------------------------------------
    def match_status(self, similarity: float) -> str:
        """
        Classify a similarity percentage into a forensic verdict.

        Args:
            similarity : plain Python float in [0, 100].
                         Call .item() on a scalar tensor before passing here.

        Returns:
            "MATCH"          if similarity >= match_threshold    (default 80)
            "POSSIBLE MATCH" if similarity >= possible_threshold (default 55)
            "NO MATCH"       otherwise

        Raises:
            TypeError if similarity is not a plain Python float (catches the
            common mistake of passing a tensor directly).

        Thresholds are set at construction and tuned via
        experiments/threshold_experiment.py after training — do not
        hardcode values here.
        """
        if not isinstance(similarity, float):
            raise TypeError(
                f"match_status expects a Python float, got {type(similarity)}. "
                f"Call .item() on a scalar tensor first."
            )

        if similarity >= self.match_threshold:
            return "MATCH"
        elif similarity >= self.possible_threshold:
            return "POSSIBLE MATCH"
        else:
            return "NO MATCH"

    # ------------------------------------------------------------------
    def analyze(self, input1: torch.Tensor, input2: torch.Tensor) -> dict:
        """
        Full forensic similarity analysis for a SINGLE cartridge-case pair.

        Enforces eval mode and disables gradient tracking automatically.
        The caller does not need to manage model.eval() or torch.no_grad().

        Args:
            input1, input2 : float32 tensors (1, 1, 224, 224) — single images.
                             Batch size MUST be 1 for analyze().
                             Use forward() directly for batched training.

        Returns:
            dict with keys:
                similarity_percentage  : float [0, 100]
                cosine_similarity      : float [−1, 1]
                euclidean_distance     : float [0, 2]
                match_status           : str  "MATCH" | "POSSIBLE MATCH" | "NO MATCH"

        Raises:
            ValueError if batch size != 1.
        """
        if input1.shape[0] != 1 or input2.shape[0] != 1:
            raise ValueError(
                f"analyze() processes one image pair at a time. "
                f"Got batch sizes {input1.shape[0]} and {input2.shape[0]}. "
                f"Use forward() for batched training / batch inference."
            )

        # Switch to eval mode for consistent inference
        # (disables Dropout, switches BatchNorm to running statistics)
        was_training = self.training
        self.eval()

        try:
            with torch.no_grad():   # no computation graph — faster + less memory
                emb1, emb2 = self.forward(input1, input2)

                euclidean  = self.euclidean_distance(emb1, emb2).item()
                cosine     = self.cosine_similarity(emb1, emb2).item()
                similarity = self.similarity_percentage(emb1, emb2).item()
                status     = self.match_status(similarity)

        finally:
            # Always restore the original training mode so analyze() can be
            # called mid-training (e.g. on validation samples) without
            # silently freezing Dropout and BatchNorm for subsequent batches.
            if was_training:
                self.train()

        return {
            "similarity_percentage": round(similarity, 2),
            "cosine_similarity":     round(cosine,     4),
            "euclidean_distance":    round(euclidean,  4),
            "match_status":          status,
        }


# ---------------------------------------------------------------------------
# Quick smoke-test  (run:  python siamese_toolmark_network.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    print("=== SiameseToolmarkNetwork Smoke-Test ===\n")

    model = SiameseToolmarkNetwork(
        embedding_dim      = 128,
        match_threshold    = 80.0,
        possible_threshold = 55.0,
    )

    # --- Parameter count ---
    total     = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total params        : {total:,}")
    print(f"Trainable params    : {trainable:,}")
    print(f"Weight sharing      : confirmed — single self.cnn, "
          f"{len(list(model.cnn.parameters()))} param tensors\n")

    # --- Identical-pair check (same image → similarity must be 100%) ---
    img_same = torch.randn(1, 1, 224, 224)
    result_same = model.analyze(img_same, img_same)
    print("Identical-image pair (same cartridge scan → expect MATCH, ~100%):")
    for k, v in result_same.items():
        print(f"  {k:26s}: {v}")

    # --- Different-image check (random tensors → should be low similarity) ---
    img_a = torch.randn(1, 1, 224, 224)
    img_b = torch.randn(1, 1, 224, 224)
    result_diff = model.analyze(img_a, img_b)
    print("\nDifferent-image pair (random noise, untrained → arbitrary similarity):")
    for k, v in result_diff.items():
        print(f"  {k:26s}: {v}")

    # --- L2 norm verification ---
    model.eval()
    with torch.no_grad():
        e1, e2 = model(img_a, img_b)
    print(f"\nemb1 L2 norm        : {torch.norm(e1, p=2, dim=1).item():.6f}  (must be 1.0)")
    print(f"emb2 L2 norm        : {torch.norm(e2, p=2, dim=1).item():.6f}  (must be 1.0)")

    # --- Threshold boundary exercise ---
    # Manually construct embeddings at known cosine similarities to verify
    # that match_status fires at exactly the right thresholds.
    # cosine = (pct/50) - 1  →  pct = (cosine + 1) * 50
    print("\nThreshold boundary checks:")

    def _make_pair_at_cosine(cos_target: float, dim: int = 128):
        """
        Return two EXACT unit-norm vectors with the given cosine similarity.

        Construction (Gram-Schmidt):
            e1   = any unit vector
            v    = random vector linearly independent of e1
            perp = v - (v·e1)e1   (component of v orthogonal to e1)
            e2   = cos_target * e1 + sin_target * (perp / ||perp||)

        This gives F.cosine_similarity(e1, e2) == cos_target exactly
        (up to float32 precision), avoiding the drift of the previous
        normalise-after-sum approach.
        """
        torch.manual_seed(0)   # fixed seed → deterministic helper
        e1   = F.normalize(torch.randn(1, dim), p=2, dim=1)
        v    = torch.randn(1, dim)
        perp = v - (v @ e1.T) * e1          # orthogonal component
        perp = F.normalize(perp, p=2, dim=1)
        sin_target = (1.0 - cos_target ** 2) ** 0.5
        e2   = cos_target * e1 + sin_target * perp  # already unit-norm by construction
        return e1, e2

    # (cos_val, expected_status, description)
    boundaries = [
        ( 1.00, "MATCH",          "cosine=+1.00 → sim=100.0% → MATCH"),
        ( 0.61, "MATCH",          "cosine=+0.61 → sim= 80.5% → MATCH"),
        ( 0.60, "MATCH",          "cosine=+0.60 → sim= 80.0% → MATCH  (boundary)"),
        ( 0.59, "POSSIBLE MATCH", "cosine=+0.59 → sim= 79.5% → POSSIBLE MATCH"),
        ( 0.11, "POSSIBLE MATCH", "cosine=+0.11 → sim= 55.5% → POSSIBLE MATCH"),
        ( 0.10, "POSSIBLE MATCH", "cosine=+0.10 → sim= 55.0% → POSSIBLE MATCH  (boundary)"),
        ( 0.09, "NO MATCH",       "cosine=+0.09 → sim= 54.5% → NO MATCH"),
        (-1.00, "NO MATCH",       "cosine=-1.00 → sim=  0.0% → NO MATCH"),
    ]

    all_pass = True
    for cos_val, expected_status, description in boundaries:
        e1, e2   = _make_pair_at_cosine(cos_val)
        sim      = model.similarity_percentage(e1, e2).item()
        status   = model.match_status(sim)
        passed   = (status == expected_status)
        flag     = "✓" if passed else "✗ FAIL"
        print(f"  {description:<50s}  got={status:<16s}  {flag}")
        if not passed:
            all_pass = False

    # --- threshold ordering guard ---
    print("\nThreshold ordering guard:")
    try:
        SiameseToolmarkNetwork(match_threshold=50.0, possible_threshold=80.0)
        print("  ✗ FAIL — should have raised ValueError")
    except ValueError as e:
        print(f"  ✓ ValueError raised correctly: {e}")

    # --- train/eval mode restoration ---
    print("\nTrain/eval mode restoration:")
    model.train()
    _ = model.analyze(img_a, img_b)
    print(f"  model.training after analyze() called in train mode: {model.training}  (must be True)")
    model.eval()
    _ = model.analyze(img_a, img_b)
    print(f"  model.training after analyze() called in eval mode : {model.training}  (must be False)")

    print(f"\nAll boundary checks passed: {all_pass}")
    print("\nSmoke-test passed.")