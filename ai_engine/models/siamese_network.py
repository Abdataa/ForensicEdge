import torch
import torch.nn as nn
import torch.nn.functional as F

from ai_engine.models.cnn_feature_extractor import FingerprintCNN


# ---------------------------------------------------------------------------
# SiameseNetwork
# ---------------------------------------------------------------------------
class SiameseNetwork(nn.Module):
    """
    Siamese Network for forensic fingerprint and toolmark similarity matching.

    Architecture
    ------------
    Two images pass through the SAME FingerprintCNN (shared weights).
    The resulting L2-normalised embeddings are compared using:
        - Euclidean distance       (lower  → more similar)
        - Cosine similarity        (higher → more similar, range [−1, 1])
        - Similarity percentage    (cosine mapped to [0, 100])

    Why shared weights matter
    -------------------------
    A single self.cnn object is used for both branches.  This guarantees true
    weight sharing — any gradient update from one branch immediately affects
    the other.  Using two separate CNN instances (self.cnn1 / self.cnn2)
    would give two independent networks, not a Siamese network.

    Training vs inference mode
    --------------------------
    During training  : call model.train() — Dropout active, BN uses batch stats.
    During inference : call model.eval()  — Dropout disabled, BN uses running stats.
    The analyze() method enforces eval mode and torch.no_grad() automatically.
    Always restore training mode afterwards if needed (model.train()).

    Threshold calibration
    ---------------------
    match_threshold and possible_threshold are constructor parameters so they
    can be tuned via experiments/threshold_experiment.py without touching this
    file.  The defaults (85 / 60) map to cosine similarities of 0.70 / 0.20
    respectively (formula: cosine = (pct / 50) − 1).

    Parameters
    ----------
    embedding_dim      : embedding size forwarded to FingerprintCNN (default 256).
    dropout_fc         : FC dropout forwarded to FingerprintCNN (default 0.3).
    dropout_spatial    : spatial dropout forwarded to FingerprintCNN (default 0.1).
    match_threshold    : similarity% above which a pair is "MATCH" (default 85).
    possible_threshold : similarity% above which a pair is "POSSIBLE MATCH" (default 60).
    """

    def __init__(
        self,
        embedding_dim:      int   = 256,
        dropout_fc:         float = 0.3,
        dropout_spatial:    float = 0.1,
        match_threshold:    float = 85.0,
        possible_threshold: float = 60.0,
    ):
        super().__init__()

        # Thresholds stored as plain floats (not tensors) for if/elif comparisons
        self.match_threshold    = match_threshold
        self.possible_threshold = possible_threshold

        # Single shared CNN backbone — both branches use this same object.
        # Weight sharing is automatic: one object → one set of parameters.
        self.cnn = FingerprintCNN(
            embedding_dim   = embedding_dim,
            dropout_fc      = dropout_fc,
            dropout_spatial = dropout_spatial,
        )

    # ------------------------------------------------------------------
    def forward_once(self, x: torch.Tensor) -> torch.Tensor:
        """
        Pass one image through the shared CNN and return its embedding.

        Note: FingerprintCNN.forward() already applies F.normalize(p=2).
        No second normalisation is needed here.
        """
        return self.cnn(x)   # shape: (B, embedding_dim), unit-norm

    # ------------------------------------------------------------------
    def forward(
        self,
        input1: torch.Tensor,
        input2: torch.Tensor,
    ):
        """
        Forward pass for training.

        Args:
            input1, input2 : float32 tensors (B, 1, 224, 224), values in [−1, 1].

        Returns:
            (emb1, emb2) : pair of unit-norm embedding tensors (B, embedding_dim).
            Both are passed directly to the loss function in train.py.
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
        Range: [0, 2] for unit-norm embeddings (since ||emb||=1 for both).
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

        Threshold mapping:
            100% → cosine =  1.0  (identical embeddings)
             85% → cosine =  0.70 (MATCH boundary)
             60% → cosine =  0.20 (POSSIBLE MATCH boundary)
              0% → cosine = −1.0  (opposite embeddings)
        """
        cos = self.cosine_similarity(emb1, emb2)
        return ((cos + 1.0) / 2.0) * 100.0

    # ------------------------------------------------------------------
    def match_status(self, similarity: float) -> str:
        """
        Classify a similarity percentage into a forensic match category.

        Args:
            similarity : plain Python float in [0, 100].
                         Call .item() on a scalar tensor before passing here.

        Returns:
            "MATCH"          if similarity >= match_threshold    (default 85)
            "POSSIBLE MATCH" if similarity >= possible_threshold (default 60)
            "NO MATCH"       otherwise

        Thresholds are set at construction and tuned via
        experiments/threshold_experiment.py — do not hardcode values here.
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
        Full forensic similarity analysis for a SINGLE image pair.

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
                f"Use forward() for batched inference."
            )

        # Switch to eval mode for inference
        # (disables Dropout, uses BatchNorm running statistics)
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
            # Always restore the original mode so training can continue
            # if analyze() is called mid-training (e.g. for validation samples)
            if was_training:
                self.train()

        return {
            "similarity_percentage": round(similarity, 2),
            "cosine_similarity":     round(cosine,     4),
            "euclidean_distance":    round(euclidean,  4),
            "match_status":          status,
        }


# ---------------------------------------------------------------------------
# Quick smoke-test  (run:  python siamese_network.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    model = SiameseNetwork(
        embedding_dim      = 256,
        match_threshold    = 85.0,
        possible_threshold = 60.0,
    )

    # Two random single-image tensors (batch=1, 1 channel, 224x224)
    img1 = torch.randn(1, 1, 224, 224)
    img2 = torch.randn(1, 1, 224, 224)

    result = model.analyze(img1, img2)

    print("=== Forensic Analysis Result ===")
    for key, value in result.items():
        print(f"  {key:26s}: {value}")

    # Verify shared weights — both branches must have identical parameters
    params = list(model.cnn.parameters())
    print(f"\nShared CNN parameters : {sum(p.numel() for p in params):,}")
    print("Weight sharing        : confirmed (single self.cnn object)")

    # Verify L2 norms of embeddings
    model.eval()
    with torch.no_grad():
        e1, e2 = model(img1, img2)
    print(f"emb1 L2 norm          : {torch.norm(e1, p=2, dim=1).item():.6f}  (should be 1.0)")
    print(f"emb2 L2 norm          : {torch.norm(e2, p=2, dim=1).item():.6f}  (should be 1.0)")

    print("\nSmoke-test passed.")
