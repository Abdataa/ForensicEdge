"""
ai_engine/inference/compare.py
--------------------------------
Top-level entry point for the ForensicEdge inference pipeline.

This is the ONLY file the FastAPI backend imports from the ai_engine.
It exposes:
    - get_engine()  : returns the singleton ForensicInferenceEngine
    - compare_images() : full two-image forensic analysis
    - extract_embedding() : single-image embedding extraction

Singleton pattern
-----------------
get_engine() creates the ForensicInferenceEngine on first call and
returns the same instance on every subsequent call.  This ensures model
weights are loaded from disk exactly once — at application startup —
not on every API request.

In FastAPI this is triggered by the lifespan event in app/main.py:

    from ai_engine.inference.compare import get_engine

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        get_engine()        # load model once at startup
        yield
        # (cleanup if needed)

    app = FastAPI(lifespan=lifespan)

Then in route handlers:

    from ai_engine.inference.compare import compare_images

    @router.post("/compare")
    async def compare(file1: UploadFile, file2: UploadFile):
        bytes1 = await file1.read()
        bytes2 = await file2.read()
        result = compare_images(bytes1, bytes2)
        return result
"""

from pathlib import Path
from ai_engine.inference.feature_extractor import ForensicInferenceEngine


# ---------------------------------------------------------------------------
# Default weights path — matches CHECKPOINT_DIR in train_siamese.py
# ---------------------------------------------------------------------------
_DEFAULT_WEIGHTS = Path("ai_engine/models/weights/best_model.pth")

# Module-level singleton — None until get_engine() is first called
_engine: ForensicInferenceEngine | None = None


# ---------------------------------------------------------------------------
def get_engine(
    weights_path: str | Path = _DEFAULT_WEIGHTS,
    embedding_dim: int = 256,
) -> ForensicInferenceEngine:
    """
    Return the singleton ForensicInferenceEngine, creating it on first call.

    Args:
        weights_path  : path to best_model.pth (default matches train_siamese.py).
        embedding_dim : must match the value used during training (default 256).

    Returns:
        The shared ForensicInferenceEngine instance.

    Notes:
        Thread-safe for read operations (inference).  The singleton is
        initialised once at startup before any requests arrive, so there
        is no race condition in practice.
    """
    global _engine
    if _engine is None:
        _engine = ForensicInferenceEngine(
            weights_path  = weights_path,
            embedding_dim = embedding_dim,
        )
    return _engine


# ---------------------------------------------------------------------------
def compare_images(image_input_1, image_input_2) -> dict:
    """
    Full forensic similarity analysis between two images.

    This is the primary function called by the FastAPI compare route.

    Args:
        image_input_1, image_input_2 : file paths (str/Path) or raw bytes.
            Raw bytes are produced by:  bytes1 = await file1.read()

    Returns:
        dict — ready for direct JSON serialisation by FastAPI:
            {
                "similarity_percentage": 87.34,
                "cosine_similarity":     0.7468,
                "euclidean_distance":    0.7124,
                "match_status":          "MATCH"
            }

    Example (FastAPI route)
    -----------------------
        from ai_engine.inference.compare import compare_images

        @router.post("/api/v1/compare")
        async def compare_endpoint(file1: UploadFile, file2: UploadFile):
            bytes1 = await file1.read()
            bytes2 = await file2.read()
            return compare_images(bytes1, bytes2)
    """
    return get_engine().compare(image_input_1, image_input_2)


# ---------------------------------------------------------------------------
def extract_embedding(image_input):
    """
    Extract a 256-dim L2-normalised embedding from a single image.

    Used by the backend when pre-computing and storing reference embeddings
    in the database (FeatureSets table) for fast batch comparison.

    Args:
        image_input : file path (str/Path) or raw bytes.

    Returns:
        float32 tensor  (1, 256), unit-norm, on CPU.

    Example (backend service)
    -------------------------
        from ai_engine.inference.compare import extract_embedding

        embedding = extract_embedding(image_bytes)
        # store embedding.numpy().tolist() in database
    """
    return get_engine().extract_embedding(image_input)


# ---------------------------------------------------------------------------
# Smoke-test  (run:  python -m ai_engine.inference.compare)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import torch

    print("ForensicEdge Inference Pipeline — smoke-test")
    print("=" * 50)

    # Check weights exist before running
    if not _DEFAULT_WEIGHTS.exists():
        print(f"WARNING: weights not found at {_DEFAULT_WEIGHTS}")
        print("Run train_siamese.py first, then re-run this test.")
    else:
        engine = get_engine()

        # Create two random tensors as stand-ins for real image bytes
        # (in real use, pass actual image bytes or file paths)
        import numpy as np
        dummy_img = (np.random.rand(224, 224) * 255).astype(np.uint8)

        import cv2, io
        _, buf1 = cv2.imencode(".png", dummy_img)
        _, buf2 = cv2.imencode(".png", dummy_img)

        bytes1 = buf1.tobytes()
        bytes2 = buf2.tobytes()

        # Same image compared to itself — should give ~100% similarity
        result = compare_images(bytes1, bytes2)

        print("\nSame image vs itself:")
        for key, value in result.items():
            print(f"  {key:26s}: {value}")

        emb = extract_embedding(bytes1)
        print(f"\nEmbedding shape : {emb.shape}")
        print(f"L2 norm         : {torch.norm(emb, p=2, dim=1).item():.6f}  (should be 1.0)")
        print("\nSmoke-test passed.")