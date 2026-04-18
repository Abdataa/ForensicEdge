/**
 * src/components/forensic/ImageUploader.tsx
 * ────────────────────────────────────────────
 * Drag-and-drop / click-to-browse evidence image uploader.
 *
 * Lifecycle stages
 * ─────────────────
 *   idle       → drop zone shown, awaiting file selection
 *   uploading  → file bytes being sent; upload progress bar (0-100 %)
 *   processing → polling GET /images/{id} every 2 s; shows pipeline status
 *   ready      → image embedded and available for comparison; green check
 *   failed     → any stage failed; red X; "Try again" resets to idle
 *
 * Pipeline status messages (shown during 'processing' stage)
 * ────────────────────────────────────────────────────────────
 *   uploaded      → "Uploaded — starting preprocessing…"
 *   preprocessing → "Running bilateral filter, CLAHE, ridge enhancement…"
 *   preprocessed  → "Enhancement done — extracting CNN embeddings…"
 *   extracting    → "Extracting feature embeddings…"
 *   ready         → "Ready for comparison"
 *   failed        → "Processing failed — please re-upload"
 *
 * Props
 * ──────
 *   evidenceType — "fingerprint" | "toolmark"  (passed to upload API)
 *   onComplete   — called with the final ImageResponse when status=ready
 *   label        — optional heading above the drop zone
 *                  e.g. "Query image" | "Reference image"
 *
 * Usage
 * ──────
 *   <ImageUploader
 *     evidenceType={evidenceType}
 *     label="Query image (evidence to identify)"
 *     onComplete={(img) => setQueryImage(img)}
 *   />
 */

import {
  useState,
  useRef,
  useCallback,
  DragEvent,
  ChangeEvent,
} from "react";
import { Upload, CheckCircle, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import clsx  from "clsx";

import {
  imageService,
  ImageResponse,
  ImageStatus,
  EvidenceType,
} from "../../services/imageService";
import Spinner from "../ui/Spinner";

// ── Types ────────────────────────────────────────────────────────────────────

type UploadStage = "idle" | "uploading" | "processing" | "ready" | "failed";

interface ImageUploaderProps {
  evidenceType: EvidenceType;
  onComplete?:  (image: ImageResponse) => void;
  /** Heading rendered above the drop zone */
  label?:       string;
}

// ── Pipeline status messages ──────────────────────────────────────────────────

const STATUS_MESSAGES: Record<ImageStatus, string> = {
  uploaded:      "Uploaded — starting preprocessing…",
  preprocessing: "Running bilateral filter, CLAHE, ridge enhancement…",
  preprocessed:  "Enhancement done — extracting CNN embeddings…",
  extracting:    "Extracting feature embeddings…",
  ready:         "Ready for comparison ✓",
  failed:        "Processing failed — please re-upload",
};

// ── Drop zone border colours per stage ───────────────────────────────────────

const STAGE_BORDER: Record<UploadStage, string> = {
  idle:       "border-gray-700 hover:border-gray-500",
  uploading:  "border-blue-600",
  processing: "border-yellow-600",
  ready:      "border-green-600",
  failed:     "border-red-600",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function ImageUploader({
  evidenceType,
  onComplete,
  label,
}: ImageUploaderProps) {
  const inputRef                  = useRef<HTMLInputElement>(null);
  const [stage,     setStage]     = useState<UploadStage>("idle");
  const [progress,  setProgress]  = useState(0);
  const [imgStatus, setImgStatus] = useState<ImageStatus | null>(null);
  const [image,     setImage]     = useState<ImageResponse | null>(null);
  const [preview,   setPreview]   = useState<string | null>(null);
  const [dragging,  setDragging]  = useState(false);

  // ── Core upload + poll pipeline ───────────────────────────────────────────
  const processFile = useCallback(async (file: File) => {
    // Show local preview immediately — before the upload even starts
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);

    setStage("uploading");
    setProgress(0);
    setImgStatus(null);

    try {
      // Step 1: upload the file
      const uploaded = await imageService.upload(
        file,
        evidenceType,
        (pct) => setProgress(pct),
      );

      // Step 2: poll until ready or failed
      setStage("processing");
      setImgStatus(uploaded.status as ImageStatus);

      const ready = await imageService.pollUntilReady(
        uploaded.id,
        (status) => setImgStatus(status),
         undefined, // intervalMs (default 2_000)
        30000,    // timeoutMs
      );

      // Done
      setStage("ready");
      setImgStatus("ready");
      setImage(ready);
      onComplete?.(ready);
      toast.success("Image ready for comparison.");

    } catch (err) {
      setStage("failed");
      setImgStatus("failed");
      const msg = err instanceof Error
        ? err.message
        : "Upload failed. Please try again.";
      toast.error(msg);
    }
  }, [evidenceType, onComplete]);

  // ── Drag handlers ─────────────────────────────────────────────────────────
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(true);
  };
  const handleDragLeave = () => setDragging(false);
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  // ── Click to browse ───────────────────────────────────────────────────────
  const handleClick = () => {
    if (stage === "idle") inputRef.current?.click();
  };
  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  // ── Reset to idle ─────────────────────────────────────────────────────────
  const reset = () => {
    setStage("idle");
    setProgress(0);
    setImgStatus(null);
    setImage(null);
    setPreview(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-2">

      {/* Optional label */}
      {label && (
        <p className="field-label">{label}</p>
      )}


      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload evidence image"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        onKeyDown={(e) => e.key === "Enter" && handleClick()}
        className={clsx(
          // Base layout
          "relative flex flex-col items-center justify-center gap-3",
          "min-h-[180px] p-6 rounded-xl border-2 border-dashed",
          "transition-all duration-150 bg-gray-800/30",
          // Cursor
          stage === "idle" ? "cursor-pointer" : "cursor-default",
          // Border colour per stage
          STAGE_BORDER[stage],
          // Dragging highlight
          dragging && "border-blue-400 bg-blue-950/20",
        )}
      >
        {/* Hidden file input */}
        <input

          ref={inputRef}
          type="file"
          accept=".bmp,.png,.jpg,.jpeg"
          className="hidden"
          onChange={handleInputChange}
          aria-label="Upload evidence image"
        />

        {/* Local image preview */}
        {preview && (
          <img
            src={preview}
            alt="Evidence preview"
            className="max-h-20 max-w-full rounded-lg object-contain"
          />
        )}

        {/* Stage icon */}
        {stage === "idle" && !preview && (
          <Upload size={32} className="text-gray-600" />
        )}
        {(stage === "uploading" || stage === "processing") && (
          <Spinner size="md" />
        )}
        {stage === "ready" && (
          <CheckCircle size={28} className="text-green-400" />
        )}
        {stage === "failed" && (
          <XCircle size={28} className="text-red-400" />
        )}

        {/* Idle instructions */}
        {stage === "idle" && (
          <div className="text-center space-y-1">
            <p className="text-gray-400 text-sm">
              Drag & drop or{" "}
              <span className="text-blue-400 underline underline-offset-2">
                browse
              </span>
            </p>
            <p className="text-gray-600 text-xs">
              {evidenceType === "fingerprint" ? "Fingerprint" : "Toolmark"} image
              {" · "}BMP, PNG, JPG{" · "}Max 10 MB
            </p>
          </div>
        )}

        {/* Upload progress bar */}
        {stage === "uploading" && (
          <div className="w-full space-y-1.5">
            <div className="flex justify-between text-xs text-gray-500">
              <span>Uploading…</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Pipeline status message */}
        {imgStatus && stage === "processing" && (
          <p className="text-yellow-400 text-xs text-center">
            {STATUS_MESSAGES[imgStatus]}
          </p>
        )}
        {imgStatus === "ready" && stage === "ready" && (
          <p className="text-green-400 text-xs text-center">
            {STATUS_MESSAGES.ready}
          </p>
        )}
        {imgStatus === "failed" && stage === "failed" && (
          <p className="text-red-400 text-xs text-center">
            {STATUS_MESSAGES.failed}
          </p>
        )}

      </div>

      {/* Below the drop zone: image metadata + actions */}
      {image && stage === "ready" && (
        <div className="flex items-center justify-between text-xs text-gray-500 px-1">
          <span>
            ID: {image.id}
            {" · "}
            {(image.file_size_bytes / 1024).toFixed(1)} KB
            {" · "}
            {image.original_filename}
          </span>
          <button
            onClick={reset}
            className="text-blue-400 hover:text-blue-300 transition-colors"
          >
            Replace
          </button>
        </div>
      )}

      {stage === "failed" && (
        <button
          onClick={reset}
          className="text-red-400 hover:text-red-300 text-xs transition-colors px-1"
        >
          ↩ Try again
        </button>
      )}

    </div>
  );
}