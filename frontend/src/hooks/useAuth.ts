/**
 * src/hooks/useAuth.ts
 * ─────────────────────
 * Convenience re-export so components can import from either location:
 *
 *   import { useAuth } from "../context/AuthContext";  // direct
 *   import { useAuth } from "../hooks/useAuth";        // via hook folder
 *
 * Both resolve to the same function.
 * Using the hooks/ path is preferred inside page components because
 * it keeps the import consistent with other custom hooks.
 */
export { useAuth } from "../context/AuthContext";