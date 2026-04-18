/**
 * src/components/ui/Spinner.tsx
 * ───────────────────────────────
 * Reusable loading spinner used throughout the dashboard.
 *
 * Exports
 * ────────
 *   Spinner      — inline spinner, three sizes (sm / md / lg)
 *   PageSpinner  — full-page centred spinner shown while auth
 *                  state is loading or a page is transitioning
 *
 * Usage
 * ──────
 *   // Inline — inside a button or card
 *   <Spinner size="sm" />
 *
 *   // Medium (default) — inside a content section
 *   <Spinner />
 *
 *   // Large — centre of an empty panel
 *   <Spinner size="lg" />
 *
 *   // Full page — while session is restoring
 *   <PageSpinner />
 *
 *   // Custom colour
 *   <Spinner className="border-green-500" />
 */

import clsx from "clsx";

// ── Types ────────────────────────────────────────────────────────────────────

type SpinnerSize = "sm" | "md" | "lg";

interface SpinnerProps {
  /** Visual size of the spinner ring (default: "md") */
  size?:      SpinnerSize;
  /** Additional Tailwind classes — use to override border colour */
  className?: string;
}

// ── Size map ─────────────────────────────────────────────────────────────────

const SIZE_CLASSES: Record<SpinnerSize, string> = {
  sm: "w-4 h-4 border-2",
  md: "w-8 h-8 border-2",
  lg: "w-12 h-12 border-4",
};

// ── Spinner ───────────────────────────────────────────────────────────────────

/**
 * Animated circular spinner.
 *
 * The ring colour defaults to blue-500 / transparent.
 * Pass a className to override, e.g.:
 *   <Spinner className="border-white border-t-transparent" />
 */
export default function Spinner({
  size      = "md",
  className,
}: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={clsx(
        // Base: round, spinning
        "rounded-full animate-spin",
        // Default colour: blue ring with transparent top segment
        "border-blue-500 border-t-transparent",
        // Size
        SIZE_CLASSES[size],
        // Caller overrides
        className,
      )}
    />
  );
}

// ── PageSpinner ───────────────────────────────────────────────────────────────

/**
 * Full-page loading state.
 * Shown by:
 *   - _app.tsx while isLoading === true (session restore in progress)
 *   - ProtectedRoute while auth state is unknown
 *   - Any page that needs a hard block before rendering
 *
 * Uses the app's base background (gray-950) so it doesn't flash white.
 */
export function PageSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="flex flex-col items-center gap-4">
        <Spinner size="lg" />
        <p className="text-gray-500 text-sm tracking-wide">
          Loading ForensicEdge…
        </p>
      </div>
    </div>
  );
}