
`inference`  sits between the trained model and  FastAPI backend. three separate inference files inside `ai_engine/inference/` since they work together as a unit and each maps to a specific report stage.
how and why ? ->  explained below!.

_||__________/\_________________________
|__________________________________/----
## How the three files fit together
___________________________________


FastAPI route (routes_compare.py)
         │
         │             from ai_engine.inference.compare import compare_images
         ▼
    compare.py          ← only file FastAPI ever imports(singleton gate)
         │
         │              get_engine() → ForensicInferenceEngine
         ▼
  feature_extractor.py  ← loads model once, runs forward passes
         │
         │               preprocess_from_bytes() / preprocess_from_path()
         ▼
    preprocess.py        ← exact mirror of enhance.py pipeline




## Key design decisions explained

-> `preprocess.py` mirrors `enhance.py` exactly  — same bilateral filter, same CLAHE, same unsharp mask, same `(img - 0.5) / 0.5` standardization. If these diverge, the model receives embeddings from a different distribution than it was trained on and similarity scores become meaningless. This is the most common inference bug in student ML projects.

-> `preprocess_from_bytes()`  accepts raw bytes directly from FastAPI's `UploadFile.read()` — no temp file needed. The backend never writes the upload to disk before passing it to the AI engine.

-> `ForensicInferenceEngine` loads weights once at construction. Reloading on every request would add ~0.5s latency per comparison. The singleton in `compare.py` ensures this happens exactly once at FastAPI startup via the lifespan event.

-> `compare.py` is the only import FastAPI needs — `compare_images(bytes1, bytes2)` is one function call that handles everything. Your `routes_compare.py` stays clean with no AI logic inside it.

-> `extract_embedding()` is exposed separately for when your backend needs to pre-compute and store reference embeddings in the `FeatureSets` database table — so future comparisons against the database don't need to re-process reference images every time.