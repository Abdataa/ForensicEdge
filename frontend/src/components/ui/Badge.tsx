/**
 * src/components/ui/Badge.tsx
 * ─────────────────────────────
 * Pill-shaped labels for status, type, and role information.
 *
 * Exports
 * ────────
 *   Badge          — generic, accepts a `variant` prop
 *   EvidenceBadge  — fingerprint (blue) | toolmark (yellow)
 *   StatusBadge    — image processing pipeline status
 *   MatchBadge     — MATCH / POSSIBLE MATCH / NO MATCH
 *   RoleBadge      — admin / analyst / ai_engineer
 *   ActiveBadge    — active (green) | inactive (red)
 *
 * All badges share the same pill shape (.badge class in globals.css):
 *   border-radius: full, padding: px-2.5 py-0.5, font-size: 12px
 *
 * Usage examples
 * ───────────────
 *   // Evidence type column in image list table
 *   <EvidenceBadge type={image.evidence_type} />
 *
 *   // Processing status column
 *   <StatusBadge status={image.status} />
 *
 *   // Match result in comparison table
 *   <MatchBadge status={result.match_status} />
 *
 *   // User role in admin table
 *   <RoleBadge role={user.role} />
 *
 *   // User account state in admin table
 *   <ActiveBadge isActive={user.is_active} />
 *
 *   // Generic badge with a custom colour
 *   <Badge variant="yellow">pending</Badge>
 */

import { ReactNode } from "react";
import clsx from "clsx";
import { EvidenceType, ImageStatus } from "../../services/imageService";
import { MatchStatus }               from "../../services/compareService";

// ── Shared colour map ─────────────────────────────────────────────────────────

const COLOUR = {
  blue:   "badge-blue",
  green:  "badge-green",
  yellow: "badge-yellow",
  red:    "badge-red",
  gray:   "badge-gray",
} as const;

type Colour = keyof typeof COLOUR;

// ── Generic Badge ─────────────────────────────────────────────────────────────

interface BadgeProps {
  /** Colour preset (default: "gray") */
  variant?:   Colour;
  children:   ReactNode;
  className?: string;
}

/**
 * Base badge — use when none of the semantic exports below apply.
 */
export default function Badge({
  variant = "gray",
  children,
  className,
}: BadgeProps) {
  return (
    <span className={clsx(COLOUR[variant], className)}>
      {children}
    </span>
  );
}

// ── EvidenceBadge ─────────────────────────────────────────────────────────────

/**
 * Shows the evidence type of a forensic image.
 *   fingerprint → blue
 *   toolmark    → yellow
 */
export function EvidenceBadge({ type }: { type: EvidenceType }) {
  const colour: Colour = type === "fingerprint" ? "blue" : "yellow";
  return (
    <span className={clsx(COLOUR[colour], "capitalize")}>
      {type}
    </span>
  );
}

// ── StatusBadge ───────────────────────────────────────────────────────────────

/**
 * Maps the image processing pipeline status to a colour.
 *
 * Lifecycle:
 *   uploaded      → gray   (just received, not yet processed)
 *   preprocessing → yellow (bilateral + CLAHE + unsharp mask running)
 *   preprocessed  → blue   (enhancement done, waiting for CNN)
 *   extracting    → yellow (CNN embedding in progress)
 *   ready         → green  (embedding stored, available for comparison)
 *   failed        → red    (any stage failed)
 */
const STATUS_COLOUR: Record<ImageStatus, Colour> = {
  uploaded:      "gray",
  preprocessing: "yellow",
  preprocessed:  "blue",
  extracting:    "yellow",
  ready:         "green",
  failed:        "red",
};

export function StatusBadge({ status }: { status: ImageStatus }) {
  return (
    <span className={clsx(COLOUR[STATUS_COLOUR[status]], "capitalize")}>
      {status}
    </span>
  );
}

// ── MatchBadge ────────────────────────────────────────────────────────────────

/**
 * Maps a forensic similarity match decision to a colour.
 *
 * Thresholds (backend configurable via .env):
 *   similarity ≥ 85 → MATCH          (green)
 *   similarity ≥ 60 → POSSIBLE MATCH (yellow)
 *   otherwise       → NO MATCH       (red)
 */
const MATCH_COLOUR: Record<MatchStatus, Colour> = {
  "MATCH":          "green",
  "POSSIBLE MATCH": "yellow",
  "NO MATCH":       "red",
};

export function MatchBadge({ status }: { status: MatchStatus }) {
  return (
    <span className={COLOUR[MATCH_COLOUR[status]]}>
      {status}
    </span>
  );
}

// ── RoleBadge ─────────────────────────────────────────────────────────────────

/**
 * Maps a user role string to a colour.
 *   admin       → red    (highest privilege)
 *   ai_engineer → green  (model management)
 *   analyst     → blue   (evidence analysis)
 *   unknown     → gray   (fallback)
 */
type UserRole = "admin" | "analyst" | "ai_engineer";

const ROLE_COLOUR: Record<UserRole, Colour> = {
  admin:       "red",
  ai_engineer: "green",
  analyst:     "blue",
};

export function RoleBadge({ role }: { role: string }) {
  const colour: Colour = ROLE_COLOUR[role as UserRole] ?? "gray";
  const label = role.replace(/_/g, " ");   // "ai_engineer" → "ai engineer"
  return (
    <span className={clsx(COLOUR[colour], "capitalize")}>
      {label}
    </span>
  );
}

// ── ActiveBadge ───────────────────────────────────────────────────────────────

/**
 * Shows whether a user account is active or deactivated.
 *   true  → green "active"
 *   false → red   "inactive"
 */
export function ActiveBadge({ isActive }: { isActive: boolean }) {
  return (
    <span className={isActive ? COLOUR.green : COLOUR.red}>
      {isActive ? "active" : "inactive"}
    </span>
  );
}