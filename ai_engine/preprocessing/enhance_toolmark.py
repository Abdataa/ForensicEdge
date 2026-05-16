"""
enhance_toolmark.py
===================
Preprocessing pipeline for tool-mark topographic scans in .x3p format.

Analogous to enhance.py (fingerprint pipeline), but adapted for breech-face
impression surfaces:
  - x3p files are ZIP archives containing an XML manifest + a binary surface
    matrix of float32/float64 depth values (NOT a greyscale image).
  - Pre-processing must therefore work in the depth/height domain first,
    then convert to a uint8 image for downstream CNN consumption.

Pipeline (per image):
  1. Parse x3p (XML header + binary surface matrix)
  2. Apply the x3p mask (exclude invalid/non-BFI regions)
  3. Fill NaN / invalid depth values with the masked-region mean
  4. Remove outlier spikes (percentile clip) — same idea as bilateral denoise
  5. Plane-fit & subtract (remove global tilt)
  6. Gaussian high-pass filter (sigma=3.0 — mild, to avoid hallucinating
     micro-striations that are not in the original surface data)
  7. Normalise to [0, 255] uint8
  8. CLAHE (local contrast enhancement — identical purpose to fingerprint pipeline)
  9. Unsharp masking — MILD (1.2 / -0.2 weights, not 1.5 / -0.5).
     Aggressive sharpening can hallucinate microstriations in toolmark images,
     so we use a gentler formula than the fingerprint pipeline.
 10. Resize to TARGET_SIZE
 11. Save as PNG

Input layout (flat — no train/val/test splits at this stage):
  ai_engine/datasets/raw/toolmarks/sample_400_balanced_preprocessed/
      firearmA/   *.x3p
      firearmB/   *.x3p
      ...
      firearmZ/   *.x3p

Output layout (mirrors input subfolder names):
  ai_engine/datasets/toolmark/processed_clean/
      firearmA/   *.png
      firearmB/   *.png
      ...

Debug output (one sample per firearm, every pipeline stage saved as PNG):
  ai_engine/datasets/toolmark/debug/
      firearmA/
          <stem>_stage1_raw.png
          <stem>_stage2_clipped.png
          <stem>_stage3_detrended.png
          <stem>_stage4_highpass.png
          <stem>_stage5_uint8.png
          <stem>_stage6_clahe.png
          <stem>_stage7_unsharp.png
          <stem>_stage8_final.png

Usage:
  python enhance_toolmark.py                   # full run + debug for first sample
  python enhance_toolmark.py --debug-only      # debug images only, no full output
"""

import sys
import cv2
import numpy as np
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple
from scipy.ndimage import gaussian_filter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Raw data — flat layout: one subfolder per firearm label, no split subfolders
INPUT_DIR  = Path("ai_engine/datasets/raw/toolmarks/sample_400_balanced_preprocessed")

# Cleaned output — same flat structure, .x3p → .png
OUTPUT_DIR = Path("ai_engine/datasets/toolmark/processed_clean")

# Debug output — intermediate stage images, one sample per firearm label
DEBUG_DIR  = Path("ai_engine/datasets/toolmark/debug")

TARGET_SIZE = (224, 224)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_EXTS = {".x3p"}

# Percentile clip — removes spike/dust artefacts before plane subtraction
CLIP_LOW_PCT  = 0.5
CLIP_HIGH_PCT = 99.5

# High-pass sigma — 3.0 is intentionally milder than originally planned (5.0).
# A large sigma removes too much low-frequency structure and can make subtle
# microstriations appear more prominent than they really are in the raw scan.
HIGHPASS_SIGMA = 3.0

# Unsharp mask weights — milder than fingerprint pipeline (which uses 1.5 / -0.5).
# For toolmarks, aggressive sharpening can hallucinate microstriations.
UNSHARP_ALPHA =  1.2
UNSHARP_BETA  = -0.2


# ---------------------------------------------------------------------------
# x3p parsing helpers
# ---------------------------------------------------------------------------

def _parse_x3p_header(xml_bytes: bytes) -> dict:
    """
    Extract key metadata from main.xml inside an x3p ZIP.

    Returns:
        dtype : numpy dtype string ('float32', 'float64', 'int32', 'int16')
        nx    : number of columns
        ny    : number of rows
    """
    root = ET.fromstring(xml_bytes)

    # Namespace-agnostic tag search (handles both bare and namespaced XML)
    def _find(tag: str) -> Optional[ET.Element]:
        for elem in root.iter():
            if elem.tag.split("}")[-1] == tag:
                return elem
        return None

    data_type_elem = _find("DataType")
    if data_type_elem is not None and data_type_elem.text:
        raw_type = data_type_elem.text.strip().upper()
        dtype_map = {
            "F": "float32", "FLOAT": "float32",
            "D": "float64", "DOUBLE": "float64",
            "L": "int32",   "LONG": "int32",
            "I": "int16",   "INT": "int16",
        }
        dtype_str = dtype_map.get(raw_type, "float64")
    else:
        dtype_str = "float64"   # NIST Ames Lab files use float64

    nx_elem = _find("SizeX")
    ny_elem = _find("SizeY")
    nx = int(nx_elem.text) if nx_elem is not None else 0
    ny = int(ny_elem.text) if ny_elem is not None else 0

    return {"dtype": dtype_str, "nx": nx, "ny": ny}


def _read_x3p(path: Path) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Read an x3p file and return (surface_matrix, mask).

    surface_matrix : float64 ndarray, shape (ny, nx).
                     NaN marks invalid / missing depth points.
    mask           : uint8 ndarray, shape (ny, nx).
                     255 = valid breech-face impression region, 0 = excluded.
                     None if no mask file is present in the archive.

    Returns (None, None) on any parse or I/O failure.
    """
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())

            # ---- XML header ----
            if "main.xml" not in names:
                print(f"  WARNING: no main.xml in '{path.name}'")
                return None, None
            header = _parse_x3p_header(zf.read("main.xml"))

            nx, ny = header["nx"], header["ny"]
            dtype  = np.dtype(header["dtype"])

            if nx == 0 or ny == 0:
                print(f"  WARNING: zero-size matrix in '{path.name}'")
                return None, None

            # ---- Binary surface data ----
            # NIST x3p files store the matrix in data/data.bin,
            # row-major, little-endian. Invalid pixels are the largest
            # representable float value (not Python float('nan')).
            bin_name = "data/data.bin" if "data/data.bin" in names else None
            if bin_name is None:
                for n in names:
                    if n.endswith(".bin"):
                        bin_name = n
                        break
            if bin_name is None:
                print(f"  WARNING: no binary data in '{path.name}'")
                return None, None

            raw = zf.read(bin_name)
            expected_bytes = nx * ny * dtype.itemsize
            if len(raw) < expected_bytes:
                print(f"  WARNING: truncated binary data in '{path.name}'")
                return None, None

            surface = np.frombuffer(raw[:expected_bytes], dtype=dtype).astype(np.float64)
            surface = surface.reshape((ny, nx))

            # Replace sentinel large-float values with NaN
            if dtype.kind == "f":
                sentinel = np.finfo(dtype).max * 0.9
                surface[np.abs(surface) > sentinel] = np.nan
            elif dtype.kind in ("i", "u"):
                sentinel = np.iinfo(np.dtype(header["dtype"])).max
                surface[surface == sentinel] = np.nan

            # ---- Mask (optional) ----
            mask = None
            mask_name = "data/data.msk" if "data/data.msk" in names else None
            if mask_name is None:
                for n in names:
                    if n.endswith(".msk"):
                        mask_name = n
                        break

            if mask_name is not None:
                raw_msk = zf.read(mask_name)
                expected_msk = nx * ny
                if len(raw_msk) >= expected_msk:
                    mask = np.frombuffer(raw_msk[:expected_msk], dtype=np.uint8)
                    mask = mask.reshape((ny, nx))
                    # Convention: 0 = invalid region, any nonzero = BFI region
                    mask = (mask > 0).astype(np.uint8) * 255

            return surface, mask

    except Exception as exc:
        print(f"  ERROR reading '{path.name}': {exc}")
        return None, None


# ---------------------------------------------------------------------------
# Individual preprocessing steps
# ---------------------------------------------------------------------------

def _apply_mask(surface: np.ndarray, mask: Optional[np.ndarray]) -> np.ndarray:
    """Set pixels outside the annotated BFI region to NaN."""
    if mask is None:
        return surface
    result = surface.copy()
    result[mask == 0] = np.nan
    return result


def _fill_nans(surface: np.ndarray) -> np.ndarray:
    """Replace NaN values with the mean of all valid (non-NaN) pixels."""
    result = surface.copy()
    valid_mean = np.nanmean(result)
    if np.isnan(valid_mean):
        valid_mean = 0.0
    result[np.isnan(result)] = valid_mean
    return result


def _clip_outliers(surface: np.ndarray) -> np.ndarray:
    """
    Percentile-clip to remove spike artefacts (dust, scratches, scanner noise).
    Bottom CLIP_LOW_PCT% and top CLIP_HIGH_PCT% are clipped.
    """
    lo = np.nanpercentile(surface, CLIP_LOW_PCT)
    hi = np.nanpercentile(surface, CLIP_HIGH_PCT)
    return np.clip(surface, lo, hi)


def _subtract_plane(surface: np.ndarray) -> np.ndarray:
    """
    Least-squares plane fit and subtraction.
    Removes global tilt / curvature from scanner mounting so the
    breech-face micro-relief becomes the dominant signal.
    """
    ny, nx = surface.shape
    xs, ys = np.meshgrid(np.arange(nx, dtype=np.float64),
                         np.arange(ny, dtype=np.float64))
    valid = ~np.isnan(surface)

    X = np.column_stack([
        xs[valid].ravel(),
        ys[valid].ravel(),
        np.ones(valid.sum()),
    ])
    z = surface[valid].ravel()

    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, z, rcond=None)
        plane = coeffs[0] * xs + coeffs[1] * ys + coeffs[2]
    except np.linalg.LinAlgError:
        plane = np.zeros_like(surface)

    return surface - plane


def _gaussian_highpass(surface: np.ndarray, sigma: float = HIGHPASS_SIGMA) -> np.ndarray:
    """
    High-pass filter: surface − GaussianBlur(surface, sigma).

    Emphasises breech-face texture / micro-relief by removing the
    low-frequency shape component.

    sigma=3.0 (HIGHPASS_SIGMA) is intentionally conservative.
    A larger sigma removes more low-frequency content and risks making subtle
    microstriations appear more prominent than they actually are, which
    would mislead the model during training.
    """
    blurred = gaussian_filter(surface, sigma=sigma)
    return surface - blurred


def _to_uint8(surface: np.ndarray) -> np.ndarray:
    """Min-max normalise a float surface to [0, 255] uint8."""
    s_min = surface.min()
    s_max = surface.max()
    if s_max - s_min < 1e-12:
        return np.zeros(surface.shape, dtype=np.uint8)
    return ((surface - s_min) / (s_max - s_min) * 255.0).astype(np.uint8)


def _clahe(img: np.ndarray) -> np.ndarray:
    """CLAHE — local contrast enhancement (identical to fingerprint pipeline)."""
    clahe_obj = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe_obj.apply(img)


def _unsharp_mask(img: np.ndarray) -> np.ndarray:
    """
    Mild unsharp masking.

    Formula: UNSHARP_ALPHA * original + UNSHARP_BETA * blurred
             = 1.2 * original − 0.2 * blurred

    The fingerprint pipeline uses 1.5 / -0.5, which is too aggressive for
    toolmarks — over-sharpening can hallucinate microstriations.
    """
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
    return cv2.addWeighted(img, UNSHARP_ALPHA, blurred, UNSHARP_BETA, 0)


# ---------------------------------------------------------------------------
# Debug helper — saves every pipeline stage as a PNG for visual inspection
# ---------------------------------------------------------------------------

def _save_debug_stages(
    stages: dict,
    debug_out_dir: Path,
    stem: str,
) -> None:
    """
    Save each entry of `stages` as a PNG image.

    stages  : dict mapping stage_name → ndarray (float64 or uint8)
    Files are saved as:
        <debug_out_dir>/<stem>_stage1_<name>.png
        <debug_out_dir>/<stem>_stage2_<name>.png
        ...

    Float arrays are min-max normalised to uint8 before saving.
    All images are resized to TARGET_SIZE so stages are visually comparable.
    """
    debug_out_dir.mkdir(parents=True, exist_ok=True)
    for idx, (stage_name, arr) in enumerate(stages.items(), start=1):
        if arr is None:
            continue
        arr_vis = _to_uint8(arr) if arr.dtype != np.uint8 else arr.copy()
        arr_vis = cv2.resize(arr_vis, TARGET_SIZE)
        fname = debug_out_dir / f"{stem}_stage{idx}_{stage_name}.png"
        cv2.imwrite(str(fname), arr_vis)
    print(f"    → debug images saved to {debug_out_dir}/")


# ---------------------------------------------------------------------------
# Full preprocessing pipeline for a single file
# ---------------------------------------------------------------------------

def preprocess_x3p(
    img_path: Path,
    debug_out_dir: Optional[Path] = None,
) -> Optional[np.ndarray]:
    """
    Full preprocessing pipeline for one .x3p toolmark scan.

    Args:
        img_path      : path to the .x3p file
        debug_out_dir : if provided, save all intermediate stage PNGs here

    Returns:
        uint8 grayscale image of shape TARGET_SIZE, or None on failure.

    NOTE ON NORMALISATION:
        Pixel-level normalisation to [0.0, 1.0] and channel standardisation
        are NOT applied here — cv2.imwrite() requires uint8 [0, 255].
        Normalisation is handled at training time inside the PyTorch Dataset
        class (identical to the fingerprint pipeline).
    """
    surface, mask = _read_x3p(img_path)
    if surface is None:
        return None

    # Ordered dict of intermediate arrays for optional debug saving
    stages: dict = {}

    # Stage 1: raw — masked + NaN-filled (for a meaningful visual baseline)
    s_masked = _apply_mask(surface, mask)
    s_filled = _fill_nans(s_masked)
    stages["raw"] = s_filled.copy()

    # Stage 2: outlier clip
    s_clipped = _clip_outliers(s_filled)
    stages["clipped"] = s_clipped.copy()

    # Stage 3: plane subtraction (de-tilt / de-curve)
    s_detrended = _subtract_plane(s_clipped)
    stages["detrended"] = s_detrended.copy()

    # Stage 4: Gaussian high-pass (sigma=3.0, mild)
    s_highpass = _gaussian_highpass(s_detrended, sigma=HIGHPASS_SIGMA)
    stages["highpass"] = s_highpass.copy()

    # Stage 5: float → uint8
    img = _to_uint8(s_highpass)
    stages["uint8"] = img.copy()

    # Stage 6: CLAHE
    img = _clahe(img)
    stages["clahe"] = img.copy()

    # Stage 7: mild unsharp masking (1.2 / -0.2)
    img = _unsharp_mask(img)
    stages["unsharp"] = img.copy()

    # Stage 8: resize to TARGET_SIZE
    img = cv2.resize(img, TARGET_SIZE)
    stages["final"] = img.copy()

    # Optionally dump all stages to disk for visual inspection
    if debug_out_dir is not None:
        _save_debug_stages(stages, debug_out_dir, img_path.stem)

    return img   # uint8, shape TARGET_SIZE


# ---------------------------------------------------------------------------
# Main processor — iterates over flat firearm-label subfolders
# ---------------------------------------------------------------------------

def process_all(debug_only: bool = False) -> None:
    """
    Preprocess all .x3p files found under INPUT_DIR.

    INPUT_DIR is expected to contain one subfolder per firearm label:
        INPUT_DIR/
            firearm%/  *.x3p    (the '%' folder name is preserved as-is)
            firearmA/  *.x3p
            firearmB/  *.x3p
            ...
            firearmZ/  *.x3p

    For each firearm label:
      - Preprocessed PNGs are written to OUTPUT_DIR/<label>/
      - Debug stage images are written for the FIRST sample only to
        DEBUG_DIR/<label>/  — so you can visually validate the pipeline
        without waiting for all ~2,625 files to process.

    Args:
        debug_only : if True, only the first sample per label is processed
                     and debug images are saved; no full output is written.
                     Use this to validate the pipeline visually before a
                     full run.
    """
    if not INPUT_DIR.exists():
        print(f"ERROR: input directory not found:\n  {INPUT_DIR}")
        return

    firearm_dirs = sorted(p for p in INPUT_DIR.iterdir() if p.is_dir())
    if not firearm_dirs:
        print(f"ERROR: no subdirectories found in {INPUT_DIR}")
        return

    print(f"Found {len(firearm_dirs)} firearm label(s) under {INPUT_DIR}")
    if debug_only:
        print("Mode: DEBUG-ONLY — first sample per label, no full output written")
    else:
        print(f"Output  → {OUTPUT_DIR}")
    print(f"Debug   → {DEBUG_DIR}  (first sample per label)\n")

    total_found  = 0
    total_ok     = 0
    total_failed = 0

    for firearm_dir in firearm_dirs:
        label           = firearm_dir.name
        out_label_dir   = OUTPUT_DIR / label
        debug_label_dir = DEBUG_DIR  / label

        x3p_files = sorted(
            f for f in firearm_dir.iterdir()
            if f.is_file() and f.suffix.lower() in VALID_EXTS
        )

        if not x3p_files:
            print(f"  [{label}] WARNING: no .x3p files — skipping.")
            continue

        if not debug_only:
            out_label_dir.mkdir(parents=True, exist_ok=True)

        label_found  = 0
        label_ok     = 0
        label_failed = 0

        for idx, x3p_file in enumerate(x3p_files):

            # Debug images only for the very first sample of each label
            do_debug   = (idx == 0)
            debug_dest = debug_label_dir if do_debug else None

            # In debug-only mode, stop after the first file
            if debug_only and idx > 0:
                break

            label_found += 1
            total_found += 1

            result = preprocess_x3p(x3p_file, debug_out_dir=debug_dest)

            if result is None:
                label_failed += 1
                total_failed += 1
                print(f"  [{label}] WARNING: failed — '{x3p_file.name}'")
                continue

            if not debug_only:
                save_path = out_label_dir / (x3p_file.stem + ".png")
                cv2.imwrite(str(save_path), result)

            label_ok += 1
            total_ok += 1

        status = "OK" if label_failed == 0 else f"{label_failed} FAILED"
        print(f"  [{label}]  found={label_found}  ok={label_ok}  [{status}]")

    # Overall summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print(f"  Total found:     {total_found}")
    print(f"  Total processed: {total_ok}")
    print(f"  Total failed:    {total_failed}")
    if not debug_only:
        print(f"  Full output  → {OUTPUT_DIR}")
    print(f"  Debug images → {DEBUG_DIR}  (first sample per label)")
    print("=" * 50)
    print("\nToolmark preprocessing finished.")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    debug_only = "--debug-only" in sys.argv

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    process_all(debug_only=debug_only)