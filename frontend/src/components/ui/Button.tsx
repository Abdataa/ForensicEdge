/**
 * src/components/ui/Button.tsx
 * ──────────────────────────────
 * Reusable button used across every page and component in the dashboard.
 *
 * Variants
 * ─────────
 *   primary   — blue, main action (Login, Compare, Generate Report)
 *   secondary — gray bordered, cancel / back / pagination
 *   danger    — red, destructive actions (Delete user, Remove image)
 *   ghost     — no background, hover only (sidebar Logout button)
 *
 * Sizes
 * ──────
 *   sm — 12px text, small padding  — table row actions, pagination
 *   md — 14px text, normal padding — most form buttons   (default)
 *   lg — 16px text, large padding  — hero CTA (Run Comparison)
 *
 * States
 * ───────
 *   loading   — replaces content with a Spinner, button is disabled
 *   disabled  — reduced opacity, not-allowed cursor
 *   fullWidth — stretches to fill its container (login / change-password forms)
 *
 * Icon support
 * ─────────────
 *   icon prop — rendered to the LEFT of children
 *   icon-only — pass no children, set an aria-label for accessibility
 *
 * Usage examples
 * ───────────────
 *   // Primary, medium, full width
 *   <Button fullWidth loading={submitting} onClick={handleLogin}>
 *     Sign in
 *   </Button>
 *
 *   // Large CTA with icon
 *   <Button size="lg" icon={<GitCompare size={18} />} onClick={compare}>
 *     Run Forensic Comparison
 *   </Button>
 *
 *   // Small secondary
 *   <Button variant="secondary" size="sm" onClick={() => setPage(p => p - 1)}>
 *     Previous
 *   </Button>
 *
 *   // Danger, icon-only (table row delete)
 *   <Button variant="danger" size="sm" icon={<Trash2 size={14} />}
 *           aria-label="Delete user" onClick={() => deleteUser(u.id)} />
 *
 *   // Ghost (sidebar logout)
 *   <Button variant="ghost" icon={<LogOut size={18} />} onClick={logout}>
 *     Log out
 *   </Button>
 */

import { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "clsx";
import Spinner from "./Spinner";

// ── Props ────────────────────────────────────────────────────────────────────

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style of the button (default: "primary") */
  variant?: "primary" | "secondary" | "danger" | "ghost";

  /** Size preset (default: "md") */
  size?: "sm" | "md" | "lg";

  /**
   * When true:
   *   - Replaces all content with a <Spinner />
   *   - Sets disabled=true on the <button>
   *   - Prevents accidental double-submission
   */
  loading?: boolean;

  /**
   * Icon element rendered to the left of the button text.
   * Automatically hidden when loading=true (replaced by spinner).
   * Pass a Lucide icon: icon={<Upload size={16} />}
   */
  icon?: ReactNode;

  /** Stretches the button to 100% of its parent width */
  fullWidth?: boolean;
}

// ── Style maps ────────────────────────────────────────────────────────────────

const VARIANT_CLASSES: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: [
    "bg-blue-600 hover:bg-blue-500 active:bg-blue-700",
    "text-white",
    "border border-transparent",
  ].join(" "),

  secondary: [
    "bg-gray-800 hover:bg-gray-700 active:bg-gray-900",
    "text-gray-300 hover:text-white",
    "border border-gray-700",
  ].join(" "),

  danger: [
    "bg-red-700 hover:bg-red-600 active:bg-red-800",
    "text-white",
    "border border-transparent",
  ].join(" "),

  ghost: [
    "bg-transparent hover:bg-gray-800",
    "text-gray-400 hover:text-white",
    "border border-transparent",
  ].join(" "),
};

const SIZE_CLASSES: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "text-xs px-3 py-1.5 gap-1.5",
  md: "text-sm px-5 py-2.5 gap-2",
  lg: "text-base px-7 py-3 gap-2.5",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function Button({
  variant   = "primary",
  size      = "md",
  loading   = false,
  icon,
  fullWidth = false,
  children,
  disabled,
  className,
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={clsx(
        // Base — layout and transition
        "inline-flex items-center justify-center",
        "font-medium rounded-lg",
        "transition-colors duration-150",
        // Disabled state
        "disabled:opacity-50 disabled:cursor-not-allowed",
        // Variant
        VARIANT_CLASSES[variant],
        // Size (also sets gap between icon and text)
        SIZE_CLASSES[size],
        // Full width
        fullWidth && "w-full",
        // Caller overrides
        className,
      )}
      {...rest}
    >
      {/* Loading state — spinner replaces icon + text */}
      {loading ? (
        <>
          <Spinner size="sm" className="border-current border-t-transparent" />
          {/* Keep a non-breaking space so the button doesn't collapse width */}
          {children && <span>{children}</span>}
        </>
      ) : (
        <>
          {icon && <span className="shrink-0">{icon}</span>}
          {children && <span>{children}</span>}
        </>
      )}
    </button>
  );
}