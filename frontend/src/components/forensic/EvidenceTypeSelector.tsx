/**
 * src/components/forensic/EvidenceTypeSelector.tsx
 * ───────────────────────────────────────────────────
 * Two-button toggle for choosing the forensic evidence type.
 *
 * Used on:
 *   /upload  — sets the type for the upload form
 *   /compare — sets the type for both uploaders; changing it resets images
 *
 * Design
 * ───────
 *   Fingerprint → blue active state (matches fingerprint badge colour)
 *   Toolmark    → yellow active state (matches toolmark badge colour)
 *   Inactive    → gray, hover to white text
 *
 * Props
 * ──────
 *   value     — currently selected EvidenceType
 *   onChange  — called with the newly selected type
 *   disabled  — disables both buttons (e.g. while a comparison is running)
 */

import clsx        from "clsx";
import { EvidenceType } from "../../services/imageService";

// ── Types ────────────────────────────────────────────────────────────────────

interface EvidenceTypeSelectorProps {
  value:     EvidenceType;
  onChange:  (type: EvidenceType) => void;
  disabled?: boolean;
}

// ── Option config ─────────────────────────────────────────────────────────────

interface Option {
  value:       EvidenceType;
  label:       string;
  description: string;
  /** Tailwind classes for the active state of this button */
  activeClass: string;
}

const OPTIONS: Option[] = [
  {
    value:       "fingerprint",
    label:       "Fingerprint",
    description: "Ridge patterns and minutiae",
    activeClass: "bg-blue-600 border-blue-500 text-white",
  },
  {
    value:       "toolmark",
    label:       "Toolmark",
    description: "Striations and surface marks",
    activeClass: "bg-yellow-600 border-yellow-500 text-white",
  },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function EvidenceTypeSelector({
  value,
  onChange,
  disabled = false,
}: EvidenceTypeSelectorProps) {
  return (
    <div className="space-y-3">

      {/* Section label */}
      <p className="field-label">Evidence Type</p>

      {/* Toggle buttons */}
      <div className="grid grid-cols-2 gap-3">
        {OPTIONS.map((opt) => {
          const isSelected = value === opt.value;

          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              className={clsx(
                // Base layout
                "flex flex-col items-center justify-center gap-1",
                "py-4 px-3 rounded-xl border text-sm font-medium",
                "transition-all duration-150",
                // Disabled
                "disabled:opacity-50 disabled:cursor-not-allowed",
                // State
                isSelected
                  ? opt.activeClass
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white hover:border-gray-500",
              )}
            >
              {/* Icon emoji */}
              <span className="text-xl" aria-hidden="true">
                {opt.value === "fingerprint" ? "🔵" : "🟡"}
              </span>
              {/* Label */}
              <span>{opt.label}</span>
              {/* Sub-description */}
              <span
                className={clsx(
                  "text-xs font-normal",
                  isSelected ? "text-white/70" : "text-gray-600",
                )}
              >
                {opt.description}
              </span>
            </button>
          );
        })}
      </div>

      {/* Guidance note */}
      <p className="text-gray-600 text-xs">
        Both images in a comparison must be the same evidence type.
        The server enforces this — mismatched types return an error.
      </p>

    </div>
  );
}