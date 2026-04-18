/**
 * src/components/layout/Navbar.tsx
 * ──────────────────────────────────
 * Top navigation bar rendered inside AppLayout above every page's content.
 *
 * Structure (left → right)
 * ─────────────────────────
 *   Page title  ← passed as a prop by each page
 *   User avatar ← initials circle, coloured ring by role
 *
 * The Navbar does not contain navigation links — those are in Sidebar.
 * Its sole purpose is to:
 *   1. Tell the user which page they are on (title)
 *   2. Show who is logged in (avatar + name on wider screens)
 *
 * Avatar colour map (matches role badge colours)
 * ────────────────────────────────────────────────
 *   admin       → purple ring
 *   analyst     → blue ring
 *   ai_engineer → green ring
 */

import clsx  from "clsx";
import { useAuth } from "../../hooks/useAuth";

// ── Role avatar ring colours ──────────────────────────────────────────────────

const ROLE_RING: Record<string, string> = {
  admin:       "ring-purple-500",
  analyst:     "ring-blue-500",
  ai_engineer: "ring-green-500",
};

// ── Props ────────────────────────────────────────────────────────────────────

interface NavbarProps {
  /**
   * The current page title shown on the left side of the bar.
   * Each page passes its own title:
   *   <AppLayout title="Dashboard">  or  <AppLayout title="Upload Evidence">
   */
  title: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Navbar({ title }: NavbarProps) {
  const { user } = useAuth();

  return (
    <header
      className={clsx(
        // Height and background — matches sidebar's dark theme
        "h-14 shrink-0",
        "bg-gray-900 border-b border-gray-800",
        // Layout
        "flex items-center justify-between px-6",
      )}
    >

      {/* ── Page title ───────────────────────────────────────────────────── */}
      <h1 className="text-white font-semibold text-base leading-none">
        {title}
      </h1>

      {/* ── Right side: user info ────────────────────────────────────────── */}
      {user && (
        <div className="flex items-center gap-3">

          {/* Name — hidden on small screens to save space */}
          <span className="text-gray-400 text-sm hidden md:block truncate max-w-[160px]">
            {user.full_name}
          </span>

          {/* Avatar circle: first letter of name, role-coloured ring */}
          <div
            title={`${user.full_name} (${user.role.replace(/_/g, " ")})`}
            className={clsx(
              // Size + shape
              "w-8 h-8 rounded-full shrink-0",
              // Background + text
              "bg-blue-600 text-white text-sm font-semibold",
              // Centre the initial
              "flex items-center justify-center",
              // Role-coloured ring (2px, with a 1px gap from the circle edge)
              "ring-2 ring-offset-1 ring-offset-gray-900",
              ROLE_RING[user.role] ?? "ring-gray-600",
            )}
          >
            {user.full_name.charAt(0).toUpperCase()}
          </div>

        </div>
      )}

    </header>
  );
}