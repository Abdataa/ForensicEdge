"""
ai_engine/inference/feature_extractor.py
-----------------------------------------
Loads the trained Siamese model once and exposes a function to extract
a 256-dimensional L2-normalised embedding from a single forensic image.

Design principle — load once, call many times
---------------------------------------------
Loading model weights from disk takes ~0.5 s.  If the model were reloaded
on every API request, a 10-request/second load would spend 5 s/s just on
weight loading.  Instead, ForensicInferenceEngine is instantiated ONCE when
the FastAPI application starts (in app/main.py lifespan) and the same
instance handles all requests.

Used by
-------
    ai_engine/inference/compare.py
    backend/app/services/similarity_service.py
    backend/app/services/image_service.py
"""

import torch
from pathlib import Path

from ai_engine.models.siamese_network    import SiameseNetwork
from ai_engine.inference.preprocess      import preprocess_from_path, preprocess_from_bytes


# ---------------------------------------------------------------------------
# ForensicInferenceEngine
# ---------------------------------------------------------------------------
class ForensicInferenceEngine:
    """
    Wraps the trained SiameseNetwork for inference.

    Responsibilities
    ----------------
    - Load model weights from best_model.pth at construction time.
    - Always run in eval() mode with torch.no_grad().
    - Provide extract_embedding() for single-image feature extraction.
    - Provide compare() for full two-image forensic analysis.

    Parameters
    ----------
    weights_path  : path to best_model.pth produced by train_siamese.py.
    embedding_dim : must match the value used during training (default 256).
    device        : 'cuda', 'cpu', or None (auto-detect).

    Example (FastAPI lifespan)
    --------------------------
        engine = ForensicInferenceEngine(
            weights_path="ai_engine/models/weights/best_model.pth"
        )
        # then pass engine to route handlers via dependency injection
    """

    def __init__(
        self,
        weights_path:  str | Path,
        embedding_dim: int = 256,
        device:        str | None = None,
    ):
        self.device = torch.device(
            device if device
            else ("cuda" if torch.cuda.is_available() else "cpu")
        )

        weights_path = Path(weights_path)
        if not weights_path.exists():
            raise FileNotFoundError(
                f"Model weights not found at: {weights_path}\n"
                f"Train the model first using train_siamese.py, "
                f"then copy best_model.pth to this path."
            )

        # Build model with same config used during training
        self._model = SiameseNetwork(embedding_dim=embedding_dim).to(self.device)

        # Load trained weights — map_location handles CPU-only Colab exports
        state = torch.load(weights_path, map_location=self.device)
        self._model.load_state_dict(state)

        # Always eval() — disables Dropout, uses BatchNorm running statistics.
        # Never call model.train() on an inference engine.
        self._model.eval()

        print(
            f"ForensicInferenceEngine ready  |  "
            f"device={self.device}  |  "
            f"weights={weights_path}"
        )

    # ------------------------------------------------------------------
    def extract_embedding(self, image_input) -> torch.Tensor:
        """
        Extract a 256-dim L2-normalised embedding from a single image.

        Args:
            image_input : one of —
                - str / Path : file path to an image on disk
                - bytes      : raw image bytes from an HTTP upload

        Returns:
            float32 tensor  (1, 256)  on CPU, unit-norm (||emb|| = 1.0).

        Raises:
            TypeError     : if image_input is not a path or bytes.
            FileNotFoundError / ValueError : propagated from preprocess.py.
        """
        # Preprocess → (1, 1, 224, 224) tensor
        if isinstance(image_input, (str, Path)):
            tensor = preprocess_from_path(image_input)
        elif isinstance(image_input, bytes):
            tensor = preprocess_from_bytes(image_input)
        else:
            raise TypeError(
                f"image_input must be a file path (str/Path) or bytes. "
                f"Got: {type(image_input)}"
            )

        tensor = tensor.to(self.device)

        with torch.no_grad():
            # forward_once() passes through the shared CNN → L2-normalised embedding
            embedding = self._model.forward_once(tensor)

        # Return on CPU so callers don't need to manage device
        return embedding.cpu()

    # ------------------------------------------------------------------
    def compare(self, image_input_1, image_input_2) -> dict:
        """
        Full forensic similarity analysis between two images.

        Args:
            image_input_1, image_input_2 : file paths or raw bytes
                (same types accepted as extract_embedding).

        Returns:
            dict with keys consumed directly by the FastAPI response schema:
                similarity_percentage : float  [0.0, 100.0]
                cosine_similarity     : float  [−1.0, 1.0]
                euclidean_distance    : float  [0.0,  2.0]
                match_status          : str    "MATCH" | "POSSIBLE MATCH" | "NO MATCH"

        Notes:
            - model.eval() and torch.no_grad() are enforced inside analyze().
            - Results are rounded for clean JSON serialisation.
        """
        emb1 = self.extract_embedding(image_input_1).to(self.device)
        emb2 = self.extract_embedding(image_input_2).to(self.device)

        # analyze() enforces eval + no_grad internally (see siamese_network.py)
        # We pass (1, 256) tensors — analyze() validates batch size = 1
        with torch.no_grad():
            similarity = self._model.similarity_percentage(emb1, emb2).item()
            cosine     = self._model.cosine_similarity(emb1, emb2).item()
            euclidean  = self._model.euclidean_distance(emb1, emb2).item()
            status     = self._model.match_status(similarity)

        return {
            "similarity_percentage": round(similarity, 2),
            "cosine_similarity":     round(cosine,     4),
            "euclidean_distance":    round(euclidean,  4),
            "match_status":          status,
        }

    # ------------------------------------------------------------------
    @property
    def model(self) -> SiameseNetwork:
        """
        Direct access to the underlying model.
        Use only if you need the raw model for advanced operations
        (e.g. GradCAM heatmaps in future visualisation features).
        """
        return self._model