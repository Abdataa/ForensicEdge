/**
 * src/pages/index.tsx
 * ─────────────────────
 * Root page — smart redirect based on auth state.
 *
 * Behaviour
 * ──────────
 *   isLoading === true  → show PageSpinner (session restore in progress)
 *   user !== null       → redirect to /dashboard
 *   user === null       → redirect to /login
 *
 * Why not a simple getServerSideProps redirect?
 * ──────────────────────────────────────────────
 * Auth tokens are stored in localStorage (client-only).
 * Server-side code cannot read them, so a server redirect would
 * always go to /login even for authenticated users.
 * The client-side effect reads localStorage and redirects correctly.
 *
 * The PageSpinner prevents a flash of the empty root page while the
 * redirect is being processed — the user sees a loading state instead.
 */

import { useEffect }   from "react";
import { useRouter }   from "next/router";
import { useAuth }     from "../hooks/useAuth";
import { PageSpinner } from "../components/ui/Spinner";

export default function IndexPage() {
  const { user, isLoading } = useAuth();
  const router              = useRouter();

  useEffect(() => {
    if (isLoading) return;          // wait for session restore
    if (user)  router.replace("/dashboard");
    else       router.replace("/login");
  }, [user, isLoading, router]);

  // Always show a spinner — the redirect fires before the user
  // has time to see any content here
  return <PageSpinner />;
}