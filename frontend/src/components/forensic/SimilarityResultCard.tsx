/**
 * src/components/forensic/SimilarityResultCard.tsx
 * ───────────────────────────────────────────────────
 * Displays a completed forensic similarity analysis result.
 *
 * Visual layout (top → bottom)
 * ──────────────────────────────
 *   Large similarity percentage    — 60px font, role-coloured
 *   Match status badge             — MATCH / POSSIBLE MATCH / NO MATCH
 *   Three metrics grid             — similarity%, cosine, L2 distance
 *   Image names row                — query filename | reference filename
 *   Evidence type + timestamp      — footer row
 *   Action buttons                 — Generate PDF | Thumbs up | Thumbs down
 *
 * Card background colours
 * ────────────────────────
 *   MATCH          → green-950 background, green-700 border
 *   POSSIBLE MATCH → yellow-950 background, yellow-700 border
 *   NO MATCH       → red-950 background, red-800 border
 *
 * Props
 * ──────
 *   result            — SimilarityResponse from compareService
 *   onGenerateReport  — called when "Generate PDF Report" is clicked
 *                       (undefined = button not shown)
 *   onFeedback        — called with true (correct) or false (incorrect)
 *                       (undefined = feedback buttons not shown)
 *   isGenerating      — shows loading state on the report button
 *
 * Usage
 * ──────
 *   <SimilarityResultCard
 *     result={result}
 *     onGenerateReport={handleGenerateReport}
 *     onFeedback={handleFeedback}
 *     isGenerating={generating}
 *   />
 */

import { FileText, ThumbsUp, ThumbsDown } from "lucide-react";
import clsx from "clsx";
import { SimilarityResponse, MatchStatus } from "../../services/compareService";
import { EvidenceBadge }                   from "../ui/Badge";
import Button                              from "../ui/Button";

// ── Match status config ───────────────────────────────────────────────────────

interface StatusConfig {
  cardBg:     string;   // card background colour
  cardBorder: string;   // card border colour
  textColour: string;   // percentage + badge text colour
  badgeBg:    string;   // badge background
  badgeBorder:string;   // badge border
  label:      string;   // human-readable interpretation
}

const STATUS_CONFIG: Record<MatchStatus, StatusConfig> = {
  "MATCH": {
    cardBg:      "bg-green-950",
    cardBorder:  "border-green-700",
    textColour:  "text-green-400",
    badgeBg:     "bg-green-900/60",
    badgeBorder: "border-green-700",
    label:       "Strong match — high confidence",
  },
  "POSSIBLE MATCH": {
    cardBg:      "bg-yellow-950",
    cardBorder:  "border-yellow-700",
    textColour:  "text-yellow-400",
    badgeBg:     "bg-yellow-900/60",
    badgeBorder: "border-yellow-700",
    label:       "Possible match — further examination recommended",
  },
  "NO MATCH": {
    cardBg:      "bg-red-950",
    cardBorder:  "border-red-800",
    textColour:  "text-red-400",
    badgeBg:     "bg-red-900/60",
    badgeBorder: "border-red-800",
    label:       "No match — images are from different sources",
  },
};

// ── Props ────────────────────────────────────────────────────────────────────

interface SimilarityResultCardProps {
  result:            SimilarityResponse;
  onGenerateReport?: () => void;
  onFeedback?:       (isCorrect: boolean) => void;
  isGenerating?:     boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function SimilarityResultCard({
  result,
  onGenerateReport,
  onFeedback,
  isGenerating = false,
}: SimilarityResultCardProps) {
  const cfg = STATUS_CONFIG[result.match_status];

  return (
    <div
      className={clsx(
        "rounded-2xl border p-6 space-y-5",
        cfg.cardBg,
        cfg.cardBorder,
      )}
    >

      {/* ── Large percentage + status badge ────────────────────────────── */}
      <div className="text-center space-y-3">

        {/* Similarity percentage */}
        <p className={clsx("text-6xl font-bold tabular-nums leading-none", cfg.textColour)}>
          {result.similarity_percentage.toFixed(1)}%
        </p>

        {/* Match status pill */}
        <span
          className={clsx(
            "inline-block px-4 py-1 rounded-full",
            "text-sm font-semibold border",
            cfg.textColour,
            cfg.badgeBg,
            cfg.badgeBorder,
          )}
        >
          {result.match_status}
        </span>

        {/* Interpretation label */}
        <p className={clsx("text-xs", cfg.textColour, "opacity-70")}>
          {cfg.label}
        </p>

      </div>

      {/* ── Three metrics grid ──────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-3">
        {[
          {
            label: "Similarity",
            value: `${result.similarity_percentage.toFixed(1)}%`,
            title: "Normalised similarity score (0–100%)",
          },
          {
            label: "Cosine sim.",
            value: result.cosine_similarity.toFixed(4),
            title: "Cosine similarity between CNN embeddings (−1 to 1)",
          },
          {
            label: "L2 distance",
            value: result.euclidean_distance.toFixed(4),
            title: "Euclidean distance between unit-norm embeddings (0 to 2)",
          },
        ].map((metric) => (
          <div
            key={metric.label}
            title={metric.title}
            className="bg-black/20 rounded-xl p-3 text-center"
          >
            <p className="text-gray-400 text-xs mb-1.5">{metric.label}</p>
            <p className="text-white font-mono text-sm font-semibold">
              {metric.value}
            </p>
          </div>
        ))}
      </div>

      {/* ── Image filenames ──────────────────────────────────────────────── */}
      {(result.image_1 || result.image_2) && (
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="space-y-0.5">
            <p className="text-gray-500 uppercase tracking-wide text-[10px]">
              Query
            </p>
            <p className="text-gray-200 truncate" title={result.image_1?.original_filename}>
              {result.image_1?.original_filename ?? "—"}
            </p>
          </div>
          <div className="space-y-0.5">
            <p className="text-gray-500 uppercase tracking-wide text-[10px]">
              Reference
            </p>
            <p className="text-gray-200 truncate" title={result.image_2?.original_filename}>
              {result.image_2?.original_filename ?? "—"}
            </p>
          </div>
        </div>
      )}

      {/* ── Footer row: evidence type + timestamp ───────────────────────── */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className="capitalize">
          {result.image_1
            ? <EvidenceBadge type={result.image_1.evidence_type} />
            : "unknown type"}
        </span>
        <span>
          {new Date(result.created_at).toLocaleString()}
        </span>
      </div>

      {/* ── Action buttons ───────────────────────────────────────────────── */}
      {(onGenerateReport || onFeedback) && (
        <div className="space-y-2 pt-1">

          {/* Generate PDF report */}
          {onGenerateReport && (
            <Button
              fullWidth
              icon={<FileText size={15} />}
              loading={isGenerating}
              onClick={onGenerateReport}
            >
              {isGenerating ? "Generating PDF…" : "Generate PDF Report"}
            </Button>
          )}

          {/* Feedback buttons */}
          {onFeedback && (
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onFeedback(true)}
                className={clsx(
                  "flex items-center justify-center gap-1.5",
                  "py-2 rounded-lg text-xs font-medium",
                  "bg-black/20 hover:bg-green-900/40",
                  "text-gray-300 hover:text-green-300",
                  "border border-gray-700 hover:border-green-700",
                  "transition-colors",
                )}
              >
                <ThumbsUp size={13} />
                Correct result
              </button>

              <button
                onClick={() => onFeedback(false)}
                className={clsx(
                  "flex items-center justify-center gap-1.5",
                  "py-2 rounded-lg text-xs font-medium",
                  "bg-black/20 hover:bg-red-900/40",
                  "text-gray-300 hover:text-red-300",
                  "border border-gray-700 hover:border-red-700",
                  "transition-colors",
                )}
              >
                <ThumbsDown size={13} />
                Incorrect result
              </button>
            </div>
          )}

        </div>
      )}

    </div>
  );
}