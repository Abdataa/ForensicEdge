/**
 * src/components/layout/AppLayout.tsx
 * ──────────────────────────────────────
 * Shell layout for every authenticated page.
 *
 * What it does
 * ─────────────
 *   1. Auth guard — redirects unauthenticated visitors to /login
 *   2. Role guard — redirects users without the required role to /dashboard
 *   3. Loading state — shows PageSpinner while session is being restored
 *   4. Renders: Sidebar (left) + flex column (Navbar top + scrollable content)
 *
 * Visual structure
 * ─────────────────
 *   ┌────────────────────────────────────────────┐
 *   │  Sidebar (w-60, full height, fixed)        │
 *   │  ┌──────────────────────────────────────┐  │
 *   │  │  Navbar (h-14, page title + avatar)  │  │
 *   │  ├──────────────────────────────────────┤  │
 *   │  │                                      │  │
 *   │  │  Page content (scrollable, p-6)      │  │
 *   │  │  {children}                          │  │
 *   │  │                                      │  │
 *   │  └──────────────────────────────────────┘  │
 *   └────────────────────────────────────────────┘
 *
 * Usage (in every authenticated page file)
 * ──────────────────────────────────────────
 *   // Standard page — any authenticated user
 *   export default function DashboardPage() {
 *     return (
 *       <AppLayout title="Dashboard">
 *         <div>page content here</div>
 *       </AppLayout>
 *     );
 *   }
 *
 *   // Admin-only page
 *   export default function AdminPage() {
 *     return (
 *       <AppLayout title="User Management" requiredRole="admin">
 *         <div>admin content here</div>
 *       </AppLayout>
 *     );
 *   }
 *
 * Role guard behaviour
 * ──────────────────────
 *   requiredRole not set → any authenticated user can access the page
 *   requiredRole="admin" → only admins can access, others go to /dashboard
 *
 *   Note: the server enforces the same rules. The client guard is UX only —
 *   it prevents non-admin users from seeing the admin page layout before the
 *   API returns a 403, which would be a confusing flicker.
 */

import { ReactNode, useEffect } from "react";
import { useRouter }            from "next/router";
import { useAuth }              from "../../hooks/useAuth";
import { User }                 from "../../services/authService";
import Sidebar                  from "./Sidebar";
import Navbar                   from "./Navbar";
import { PageSpinner }          from "../ui/Spinner";

// ── Props ────────────────────────────────────────────────────────────────────

interface AppLayoutProps {
  /** Page title shown in the Navbar */
  title:        string;
  /** Page content */
  children:     ReactNode;
  /**
   * When set, only users with this role can view the page.
   * All others are silently redirected to /dashboard.
   */
  requiredRole?: User["role"];
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function AppLayout({
  title,
  children,
  requiredRole,
}: AppLayoutProps) {
  const { user, isLoading } = useAuth();
  const router              = useRouter();

  // ── Auth + role guard ──────────────────────────────────────────────────────
  useEffect(() => {
    // Don't redirect while session is still being restored
    if (isLoading) return;

    // Not logged in → login page
    if (!user) {
      router.replace("/login");
      return;
    }

    // Wrong role → dashboard (not a 403 page, just a silent redirect)
    if (requiredRole && user.role !== requiredRole) {
      router.replace("/dashboard");
    }
  }, [user, isLoading, router, requiredRole]);

  // ── Loading state ──────────────────────────────────────────────────────────
  // Show spinner while:
  //   a) Session is being restored on first mount
  //   b) Auth state is known but redirect hasn't fired yet (brief flicker guard)
  if (isLoading || !user) {
    return <PageSpinner />;
  }

  // Extra guard: if a requiredRole is set and user doesn't match,
  // render nothing while the router.replace() is in flight
  if (requiredRole && user.role !== requiredRole) {
    return null;
  }

  // ── Authenticated layout ───────────────────────────────────────────────────
  return (
    <div className="flex min-h-screen bg-gray-950">

      {/* Left sidebar — fixed width, full height */}
      <Sidebar />

      {/* Right side — flexible column */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Top bar — fixed height, shows title + user avatar */}
        <Navbar title={title} />

        {/* Scrollable page content */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {children}
        </main>

      </div>
    </div>
  );
}