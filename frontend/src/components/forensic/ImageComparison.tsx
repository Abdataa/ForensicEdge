/**
 * src/components/forensic/ImageComparison.tsx
 * ──────────────────────────────────────────────
 * Side-by-side viewer showing the original uploaded evidence image
 * alongside the preprocessed (enhanced) version.
 *
 * Shows what the AI pipeline did to the image:
 *   Original  → raw evidence as uploaded (fingerprint/toolmark)
 *   Enhanced  → after bilateral filter + CLAHE + unsharp masking
 *               resized to 224×224 (the CNN input size)
 *
 * Usage
 * ──────
 *   // Pass an image ID — component fetches both versions automatically
 *   <ImageComparison imageId={42} />
 *
 *   // Or pass a pre-fetched ComparisonResponse
 *   <ImageComparison data={comparisonData} />
 *
 * States
 * ───────
 *   Loading  — skeleton while fetching from GET /images/{id}/comparison
 *   Ready    — both images displayed side by side
 *   No enhanced — shows original only with a "preprocessing pending" note
 *   Error    — fetch failed
 */

import { useState, useEffect } from "react";
import { ZoomIn, ZoomOut, X, Info } from "lucide-react";
import toast   from "react-hot-toast";
import clsx    from "clsx";
import { imageService, ComparisonResponse, ImageStatus } from "../../services/imageService";
import Spinner from "../ui/Spinner";

// ── Processing steps displayed as tags ───────────────────────────────────────

const STEP_LABELS: Record<string, string> = {
  bilateral:    "Bilateral filter",
  clahe:        "CLAHE",
  unsharp_mask: "Unsharp masking",
  resize:       "Resize 224×224",
  normalised:   "Normalised",
};

// ── Status labels ─────────────────────────────────────────────────────────────

const STATUS_NOTE: Partial<Record<ImageStatus, string>> = {
  uploaded:      "Preprocessing has not started yet.",
  preprocessing: "Preprocessing is running — check back shortly.",
  preprocessed:  "Image enhanced. CNN embedding pending (model not trained yet).",
  extracting:    "Extracting CNN embeddings…",
  failed:        "Processing failed. Re-upload the image to try again.",
};

// ── Props ────────────────────────────────────────────────────────────────────

interface Props {
  /** Image ID — component fetches comparison data automatically */
  imageId?: number;
  /** Pre-fetched data — skips the fetch when provided */
  data?:    ComparisonResponse;
  /** Called when the user closes a full-screen zoom modal */
  onClose?: () => void;
  /** Show as a modal overlay (true) or inline card (false, default) */
  modal?:   boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ImageComparison({ imageId, data: initialData, onClose, modal }: Props) {
  const [data,    setData]    = useState<ComparisonResponse | null>(initialData ?? null);
  const [loading, setLoading] = useState(!initialData && !!imageId);
  const [error,   setError]   = useState("");
  const [zoomed,  setZoomed]  = useState<"original" | "enhanced" | null>(null);

  // Fetch comparison data if only imageId provided
  useEffect(() => {
    if (initialData || !imageId) return;
    setLoading(true);
    imageService
      .getComparison(imageId)
      .then(setData)
      .catch(() => setError("Could not load image comparison."))
      .finally(() => setLoading(false));
  }, [imageId, initialData]);

  // ── Loading ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className={clsx(
        "flex items-center justify-center gap-3 py-16",
        modal && "min-h-[300px]",
      )}>
        <Spinner size="md" />
        <p className="text-gray-400 text-sm">Loading image comparison…</p>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (error || !data) {
    return (
      <div className="text-center py-10 space-y-2">
        <p className="text-red-400 text-sm">{error || "No data available."}</p>
      </div>
    );
  }

  const hasEnhanced    = !!data.enhanced;
  const statusNote     = STATUS_NOTE[data.status];
  const processingSteps = data.enhanced?.processing ?? {};

  // ── Zoom modal ────────────────────────────────────────────────────────────
  if (zoomed) {
    const src   = zoomed === "original" ? data.original.data : data.enhanced?.data;
    const label = zoomed === "original" ? "Original" : "Enhanced";
    return (
      <div
        className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
        onClick={() => setZoomed(null)}
      >
        <div
          className="relative max-w-3xl w-full"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-white font-medium">{label} — {data.original.filename}</span>
            <button
              onClick={() => setZoomed(null)}
              className="text-gray-400 hover:text-white p-1 transition-colors"
            >
              <X size={20} />
            </button>
          </div>
          <img
            src={src}
            alt={label}
            className="w-full rounded-xl object-contain max-h-[80vh]"
            style={{ imageRendering: "pixelated" }}
          />
        </div>
      </div>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────
  const wrapper = modal
    ? "space-y-5"
    : "bg-gray-900 border border-gray-800 rounded-2xl p-5 space-y-5";

  return (
    <div className={wrapper}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold text-sm">
            Original vs Enhanced
          </h3>
          <p className="text-gray-500 text-xs mt-0.5">
            {data.original.filename} ·{" "}
            <span className="capitalize">{data.original.evidence_type}</span>
          </p>
        </div>
        {onClose && (
          <button

            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors p-1"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Side-by-side images */}
      <div className={clsx(
        "grid gap-4",
        hasEnhanced ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1 max-w-sm mx-auto",
      )}>

        {/* Original */}
        <ImagePanel
          src={data.original.data}
          label="Original"
          sublabel="As uploaded"
          badge={{ text: "Raw", colour: "bg-gray-700 text-gray-300" }}
          onZoom={() => setZoomed("original")}
        />

        {/* Enhanced */}
        {hasEnhanced ? (
          <ImagePanel
            src={data.enhanced!.data}
            label="Enhanced"
            sublabel="After preprocessing pipeline"
            badge={{ text: "AI Enhanced", colour: "bg-blue-900 text-blue-300" }}
            onZoom={() => setZoomed("enhanced")}
          />
        ) : (
          /* Placeholder when enhanced not yet available */
          <div className="relative rounded-xl border-2 border-dashed border-gray-700
                          bg-gray-800/40 flex flex-col items-center justify-center
                          gap-3 p-8 text-center">
            <Info size={28} className="text-gray-600" />
            <p className="text-gray-400 text-sm font-medium">Enhanced not available</p>
            <p className="text-gray-600 text-xs leading-relaxed">
              {statusNote ?? "Preprocessing is pending."}
            </p>
          </div>
        )}
      </div>

      {/* Processing steps tags */}
      {hasEnhanced && Object.keys(processingSteps).length > 0 && (
        <div className="space-y-2">
          <p className="text-gray-600 text-xs font-medium uppercase tracking-wide">
            Pipeline steps applied
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(processingSteps).map(([key, val]) => {
              if (key === "normalised") {
                return (
                  <StepTag key={key}
                    label={`Normalised ${val}`} />
                );
              }
              if (key === "resize" && Array.isArray(val)) {
                return (
                  <StepTag key={key}
                    label={`Resize ${val[0]}×${val[1]}`} />
                );
              }
              if (val === true) {
                return (
                  <StepTag key={key}
                    label={STEP_LABELS[key] ?? key} />
                );
              }
              return null;
            })}
          </div>
          <p className="text-gray-600 text-xs">
            These enhancements improve ridge/striation clarity for the CNN feature extractor.
          </p>
        </div>
      )}

      {/* Status note for non-enhanced */}
      {!hasEnhanced && statusNote && (
        <div className="flex items-start gap-2 bg-gray-800 rounded-xl px-4 py-3 text-xs text-gray-400">
          <Info size={13} className="mt-0.5 shrink-0 text-blue-400" />
          {statusNote}
        </div>
      )}

    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface ImagePanelProps {
  src:      string;
  label:    string;
  sublabel: string;
  badge:    { text: string; colour: string };
  onZoom:   () => void;
}

function ImagePanel({ src, label, sublabel, badge, onZoom }: ImagePanelProps) {
  return (
    <div className="space-y-2">
      {/* Label row */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-white text-sm font-medium">{label}</span>
          <span className="text-gray-600 text-xs ml-2">{sublabel}</span>
        </div>
        <span className={clsx(
          "text-xs px-2 py-0.5 rounded-full font-medium",
          badge.colour,
        )}>
          {badge.text}
        </span>
      </div>

      {/* Image */}
      <div className="relative group rounded-xl overflow-hidden bg-gray-800 border border-gray-700">
        <img
          src={src}
          alt={label}
          className="w-full object-contain max-h-72"
          style={{ imageRendering: "pixelated" }}
        />
        {/* Zoom overlay on hover */}
        <button
          onClick={onZoom}
          className="absolute inset-0 bg-black/0 group-hover:bg-black/40
                     flex items-center justify-center
                     opacity-0 group-hover:opacity-100 transition-all"
          aria-label={`Zoom ${label}`}
        >
          <div className="flex items-center gap-2 bg-black/60 text-white
                          text-xs px-3 py-1.5 rounded-full">
            <ZoomIn size={13} />
            Full screen
          </div>
        </button>
      </div>
    </div>
  );
}

function StepTag({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-lg
                     bg-blue-950/60 text-blue-300 text-xs border border-blue-800/60">
      {label}
    </span>
  );
}