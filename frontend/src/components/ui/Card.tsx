/**
 * src/components/ui/Card.tsx
 * ───────────────────────────
 * Container component used to group related content on every page.
 *
 * Variants
 * ─────────
 *   Card      — standard section container (most common)
 *   StatCard  — compact dashboard metric tile (number + label + icon)
 *
 * Card props
 * ───────────
 *   title     — section heading rendered top-left in the card header
 *   action    — node rendered top-right (e.g. "View all →" link)
 *   padding   — override the default p-6 (e.g. padding="p-0" for tables)
 *   className — additional classes for the outer div
 *
 * Usage examples
 * ───────────────
 *   // Plain container
 *   <Card>
 *     <p>Some content</p>
 *   </Card>
 *
 *   // With header (title + action link)
 *   <Card
 *     title="Recent Comparisons"
 *     action={<Link href="/compare" className="text-blue-400 text-sm">View all →</Link>}
 *   >
 *     <Table ... />
 *   </Card>
 *
 *   // Stat tile on dashboard
 *   <StatCard
 *     label="Comparisons run"
 *     value={total}
 *     icon={<GitCompare size={20} className="text-purple-400" />}
 *   />
 *
 *   // No padding (table extends to card edges)
 *   <Card title="All Users" padding="p-0">
 *     <table className="data-table"> ... </table>
 *   </Card>
 */

import { ReactNode } from "react";
import clsx from "clsx";

// ── Card ──────────────────────────────────────────────────────────────────────

interface CardProps {
  children:    ReactNode;
  /** Optional heading shown top-left of the card */
  title?:      string;
  /** Optional node shown top-right of the card (link, button, etc.) */
  action?:     ReactNode;
  /** Tailwind padding class — default "p-6" */
  padding?:    string;
  className?:  string;
}

export default function Card({
  children,
  title,
  action,
  padding   = "p-6",
  className,
}: CardProps) {
  const hasHeader = title || action;

  return (
    <div className={clsx("bg-gray-900 border border-gray-800 rounded-2xl", padding, className)}>

      {/* Card header — only rendered when title or action is provided */}
      {hasHeader && (
        <div
          className={clsx(
            "flex items-center justify-between",
            // When padding="p-0" the header needs its own padding
            padding === "p-0" ? "px-6 pt-5 pb-4" : "mb-5",
          )}
        >
          {title && (
            <h3 className="text-white font-semibold text-base leading-none">
              {title}
            </h3>
          )}
          {/* Spacer pushes action to the right when title is absent */}
          {!title && <span />}
          {action && (
            <div className="flex items-center">
              {action}
            </div>
          )}
        </div>
      )}

      {children}
    </div>
  );
}

// ── StatCard ──────────────────────────────────────────────────────────────────

interface StatCardProps {
  /** Metric label shown below the value */
  label:      string;
  /** The large number or text to display */
  value:      string | number | null;
  /** Icon element shown top-right of the tile */
  icon?:      ReactNode;
  /** Additional classes for the outer div */
  className?: string;
  /** onClick for making the tile a link-like button */
  onClick?:   () => void;
}

/**
 * Dashboard metric tile.
 * Shows a large value, a label, and an optional icon.
 *
 * Usage:
 *   <StatCard
 *     label="Total images"
 *     value={imageTotal ?? "—"}
 *     icon={<Upload size={20} className="text-blue-400" />}
 *     onClick={() => router.push("/upload")}
 *   />
 */
export function StatCard({
  label,
  value,
  icon,
  className,
  onClick,
}: StatCardProps) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        "bg-gray-900 border border-gray-800 rounded-2xl p-5",
        "flex flex-col gap-2",
        onClick && "cursor-pointer hover:border-gray-600 transition-colors",
        className,
      )}
    >
      {/* Top row: label + icon */}
      <div className="flex items-center justify-between">
        <p className="text-gray-500 text-sm">{label}</p>
        {icon && <span className="shrink-0">{icon}</span>}
      </div>

      {/* Value */}
      <p className="text-3xl font-bold text-white tabular-nums leading-none">
        {value ?? "—"}
      </p>
    </div>
  );
}