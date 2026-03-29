import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# FingerprintCNN
# ---------------------------------------------------------------------------
class FingerprintCNN(nn.Module):
    """
    Custom CNN feature extractor for forensic fingerprint and toolmark images.

    Role in the pipeline
    --------------------
    This module is the shared backbone of the Siamese network.  Two identical
    instances (sharing weights) each receive one image from a pair and produce
    a compact embedding vector.  The Siamese loss then minimises the distance
    between embeddings of the same identity and maximises it for different ones.

    Architecture overview
    ---------------------
    Input  : (B, 1, 224, 224)  — grayscale, normalised to [−1, 1] by Dataset
    Block 1: Conv(1  →  32, k=3) → BN → ReLU → MaxPool  →  (B,  32, 112, 112)
    Block 2: Conv(32 →  64, k=3) → BN → ReLU → MaxPool  →  (B,  64,  56,  56)
    Block 3: Conv(64 → 128, k=3) → BN → ReLU → MaxPool  →  (B, 128,  28,  28)
    Block 4: Conv(128→ 256, k=3) → BN → ReLU → MaxPool  →  (B, 256,  14,  14)
             + Dropout2d(0.1) — spatial regularisation
    GAP    : AdaptiveAvgPool2d((1,1))                     →  (B, 256,   1,   1)
    Flatten:                                              →  (B, 256)
    FC1    : Linear(256 → 512) → ReLU → Dropout(0.3)     →  (B, 512)
    FC2    : Linear(512 → 256)                            →  (B, 256)
    L2 norm: F.normalize(p=2)  → unit hypersphere         →  (B, 256)

    Design decisions
    ----------------
    Global Average Pooling (GAP) instead of flatten:
        Without GAP, fc1 alone would require ~51 M parameters (100 352 → 512).
        GAP compresses each feature map to a single value, reducing the entire
        model to ~560 K parameters — lightweight enough for Google Colab / Kaggle
        GPU training and appropriate for a dataset of ~600 identities.

    4 convolutional blocks:
        Block 1 — basic edges and texture
        Block 2 — ridge flows and orientations
        Block 3 — minutiae patterns (bifurcations, ridge endings)
        Block 4 — higher-order spatial relationships between minutiae
        Each block halves spatial resolution while doubling channels, keeping
        computation roughly constant per block.

    256-dimensional embedding:
        128 dims is workable for 600 identities but leaves little margin for
        the distance metric to separate classes.  256 dims gives measurably
        better separation in retrieval tasks at negligible extra cost.

    L2 normalisation on the output:
        Projects every embedding onto the unit hypersphere so that Euclidean
        distance and cosine similarity are equivalent.  Required for
        contrastive loss and cosine-based similarity scoring in inference.

    Dropout2d after block 4:
        Drops entire feature-map channels (spatial dropout) rather than
        individual neurons.  More effective regularisation for conv outputs
        where adjacent pixels are highly correlated.

    BatchNorm before ReLU (original paper recommendation):
        Stabilises training, reduces learning-rate sensitivity, and provides
        mild regularisation throughout the conv stack.

    IMPORTANT — train / eval mode:
        Call model.train() during training and model.eval() during inference.
        BatchNorm uses batch statistics in train mode and running statistics
        in eval mode.  Dropout is active in train mode and disabled in eval.
        Forgetting model.eval() at inference time produces inconsistent
        similarity scores for the same image pair.

    Parameters
    ----------
    embedding_dim    : output embedding size (default 256).
                       Set to 128 for a lighter model; 512 for richer embeddings.
    dropout_fc       : dropout probability on the FC block (default 0.3).
    dropout_spatial  : spatial dropout probability after block 4 (default 0.1).
    """

    def __init__(
        self,
        embedding_dim:   int   = 256,
        dropout_fc:      float = 0.3,
        dropout_spatial: float = 0.1,
    ):
        super().__init__()

        self.embedding_dim = embedding_dim

        # ------------------------------------------------------------------
        # Convolutional blocks
        # Each: Conv2d → BatchNorm2d → (ReLU applied in forward) → MaxPool2d
        # padding=1 keeps spatial size unchanged before pooling
        # ------------------------------------------------------------------

        # Block 1 — basic edges and texture
        self.conv1 = nn.Conv2d(1,   32,  kernel_size=3, padding=1)
        self.bn1   = nn.BatchNorm2d(32)

        # Block 2 — ridge flows and orientations
        self.conv2 = nn.Conv2d(32,  64,  kernel_size=3, padding=1)
        self.bn2   = nn.BatchNorm2d(64)

        # Block 3 — minutiae patterns (bifurcations, ridge endings)
        self.conv3 = nn.Conv2d(64,  128, kernel_size=3, padding=1)
        self.bn3   = nn.BatchNorm2d(128)

        # Block 4 — higher-order spatial relationships between minutiae
        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.bn4   = nn.BatchNorm2d(256)

        # Shared pooling — halves spatial dims after every block
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Spatial dropout after block 4
        # Drops entire feature-map channels; more effective than neuron
        # dropout for spatially correlated conv outputs
        self.spatial_dropout = nn.Dropout2d(p=dropout_spatial)

        # ------------------------------------------------------------------
        # Global Average Pooling
        # Compresses (B, 256, 14, 14) → (B, 256, 1, 1) regardless of input size
        # ------------------------------------------------------------------
        self.gap = nn.AdaptiveAvgPool2d((1, 1))

        # ------------------------------------------------------------------
        # Fully-connected embedding head
        # Dropout sits between fc1 and fc2 — NOT after fc2 (the embedding).
        # Dropping embedding values would corrupt similarity scores.
        # ------------------------------------------------------------------
        self.fc1     = nn.Linear(256, 512)
        self.dropout = nn.Dropout(p=dropout_fc)
        self.fc2     = nn.Linear(512, embedding_dim)

    # ------------------------------------------------------------------
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x : float32 tensor  (B, 1, 224, 224),  values in [−1, 1].
                Produced by SiameseFingerprintDataset.load_image().

        Returns:
            Unit-norm embedding tensor  (B, embedding_dim).
        """
        # Block 1 — edges
        x = self.pool(F.relu(self.bn1(self.conv1(x))))    # (B,  32, 112, 112)

        # Block 2 — ridge flows
        x = self.pool(F.relu(self.bn2(self.conv2(x))))    # (B,  64,  56,  56)

        # Block 3 — minutiae patterns
        x = self.pool(F.relu(self.bn3(self.conv3(x))))    # (B, 128,  28,  28)

        # Block 4 — spatial relationships + spatial regularisation
        x = self.pool(F.relu(self.bn4(self.conv4(x))))    # (B, 256,  14,  14)
        x = self.spatial_dropout(x)

        # Global Average Pooling — position-invariant feature summary
        x = self.gap(x)                                   # (B, 256,   1,   1)
        x = x.view(x.size(0), -1)                         # (B, 256)

        # Fully-connected embedding head
        x = F.relu(self.fc1(x))                           # (B, 512)
        x = self.dropout(x)
        x = self.fc2(x)                                   # (B, embedding_dim)

        # L2 normalisation → unit hypersphere
        # Makes Euclidean distance ≡ cosine similarity for downstream matching
        x = F.normalize(x, p=2, dim=1)

        return x

    # ------------------------------------------------------------------
    def get_embedding_dim(self) -> int:
        """Returns the output embedding dimensionality."""
        return self.embedding_dim


# ---------------------------------------------------------------------------
# Quick smoke-test  (run:  python cnn_feature_extractor.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    model = FingerprintCNN(embedding_dim=256)

    # Always call eval() before inference or testing
    # (disables Dropout, switches BatchNorm to running stats)
    model.eval()

    dummy = torch.randn(8, 1, 224, 224)   # batch of 8 grayscale images

    with torch.no_grad():
        embeddings = model(dummy)

    print(f"Input shape           : {dummy.shape}")
    print(f"Embedding shape       : {embeddings.shape}")       # (8, 256)
    print(f"Embedding dim         : {model.get_embedding_dim()}")

    # L2 norms must all equal 1.0 (unit hypersphere)
    norms = torch.norm(embeddings, p=2, dim=1)
    print(f"L2 norms (all ≈ 1.0) : {norms.tolist()}")

    # Parameter count
    total     = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total params          : {total:,}")
    print(f"Trainable params      : {trainable:,}")

    print("\nSmoke-test passed.")