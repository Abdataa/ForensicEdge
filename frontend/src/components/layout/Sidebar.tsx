/**
 * src/components/layout/Sidebar.tsx
 * ────────────────────────────────────
 * Left navigation sidebar — persistent on all authenticated pages
 * via AppLayout.tsx.
 *
 * Structure (top → bottom)
 * ─────────────────────────
 *   Logo + app name
 *   User info panel (name + role badge)
 *   Navigation links  ← role-filtered
 *   Log out button    ← always at the bottom
 *
 * Active link highlighting
 * ─────────────────────────
 * Uses useRouter().pathname to compare against each nav item's href.
 * Exact match only — so /compare does NOT highlight when on /compare/123.
 * Adjust with startsWith() if nested routes are added later.
 *
 * Role-based navigation
 * ──────────────────────
 * Nav items with a `roles` array are only shown to users whose role
 * is in that array.  Items without a `roles` key are shown to everyone.
 * The server enforces the same rules — the sidebar hiding is UX only.
 *
 * Role colour map (matches RoleBadge in Badge.tsx)
 * ─────────────────────────────────────────────────
 *   admin       → purple pill
 *   analyst     → blue pill
 *   ai_engineer → green pill
 */

import Link       from "next/link";
import { useRouter } from "next/router";
import {
  LayoutDashboard,
  Upload,
  GitCompare,
  FileText,
  History,
  MessageSquare,
  Users,
  KeyRound,
  LogOut,
  Shield,
} from "lucide-react";
import clsx      from "clsx";
import { useAuth } from "../../hooks/useAuth";
import Button    from "../ui/Button";

// ── Nav item definition ───────────────────────────────────────────────────────

interface NavItem {
  href:   string;
  label:  string;
  icon:   React.ReactNode;
  /** If provided, item is only shown to users with one of these roles */
  roles?: Array<"analyst" | "admin" | "ai_engineer">;
}

const NAV_ITEMS: NavItem[] = [
  {
    href:  "/dashboard",
    label: "Dashboard",
    icon:  <LayoutDashboard size={18} />,
  },
  {
    href:  "/upload",
    label: "Upload",
    icon:  <Upload size={18} />,
  },
  {
    href:  "/compare",
    label: "Compare",
    icon:  <GitCompare size={18} />,
  },
  {
    href:  "/cases",
    label: "Case Management",
    icon:  <FileText size={18} />,
  },

  {
    href:  "/reports",
    label: "Reports",
    icon:  <FileText size={18} />,
  },
  {
    href:  "/logs",
    label: "History",
    icon:  <History size={18} />,
  },
  {
    href:  "/feedback",
    label: "Feedback",
    icon:  <MessageSquare size={18} />,
  },
  {
    href:  "/change-password",
    label: "Password",
    icon:  <KeyRound size={18} />,
  },
  {
    href:   "/admin",
    label:  "User Management",
    icon:   <Users size={18} />,
    roles:  ["admin"],

  },


];

// ── Role badge colours ────────────────────────────────────────────────────────

const ROLE_CLASSES: Record<string, string> = {
  admin:       "bg-purple-900/60 text-purple-300 border border-purple-800",
  analyst:     "bg-blue-900/60   text-blue-300   border border-blue-800",
  ai_engineer: "bg-green-900/60  text-green-300  border border-green-800",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function Sidebar() {
  const { user, logout }   = useAuth();
  const { pathname }       = useRouter();

  // Filter nav items by the current user's role
  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role)),
  );

  return (
    <aside
      className={clsx(
        // Fixed width, full viewport height, dark background
        "w-60 min-h-screen shrink-0",
        "bg-gray-900 border-r border-gray-800",
        "flex flex-col",
      )}
    >

      {/* ── Logo ─────────────────────────────────────────────────────────── */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
            <Shield size={16} className="text-white" />
          </div>
          <div>
            <p className="text-white font-semibold text-sm leading-none">
              ForensicEdge
            </p>
            <p className="text-gray-600 text-xs mt-0.5">
              Evidence Analysis
            </p>
          </div>
        </div>
      </div>

      {/* ── User info ────────────────────────────────────────────────────── */}
      {user && (
        <div className="px-4 py-3 border-b border-gray-800">
          {/* Avatar + name */}
          <div className="flex items-center gap-2.5">
            <div
              className={clsx(
                "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                "bg-blue-600 text-white text-sm font-semibold",
              )}
            >
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <p className="text-white text-sm font-medium truncate leading-none">
              {user.full_name}
            </p>
          </div>

          {/* Role badge */}
          <span
            className={clsx(
              "inline-block mt-2 px-2 py-0.5 rounded-full text-xs font-medium capitalize",
              ROLE_CLASSES[user.role] ?? "bg-gray-800 text-gray-400",
            )}
          >
            {user.role.replace(/_/g, " ")}
          </span>
        </div>
      )}

      {/* ── Navigation ───────────────────────────────────────────────────── */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {visibleItems.map((item) => {
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm",
                "transition-colors duration-150",
                isActive
                  // Active: solid blue background
                  ? "bg-blue-600 text-white"
                  // Inactive: subtle hover
                  : "text-gray-400 hover:bg-gray-800 hover:text-white",
              )}
            >
              {/* Icon */}
              <span className="shrink-0">{item.icon}</span>
              {/* Label */}
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* ── Logout ───────────────────────────────────────────────────────── */}
      <div className="px-3 pb-4 border-t border-gray-800 pt-3">
        <Button
          variant="ghost"
          size="sm"
          fullWidth
          icon={<LogOut size={16} />}
          onClick={logout}
          className="justify-start text-gray-500 hover:text-red-400 hover:bg-gray-800"
        >
          Log out
        </Button>
      </div>

    </aside>
  );
}