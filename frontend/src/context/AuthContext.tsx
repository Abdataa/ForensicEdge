/**
 * src/context/AuthContext.tsx
 * ────────────────────────────
 * Global authentication state for the ForensicEdge dashboard.
 *
 * What this provides
 * ───────────────────
 *   user        — the currently authenticated User, or null
 *   isLoading   — true while the session is being restored on mount
 *   login()     — authenticates, stores tokens, navigates to /dashboard
 *   logout()    — clears tokens and navigates to /login
 *   isAdmin()   — true if user.role === "admin"
 *   isAIEngineer() — true if user.role === "ai_engineer"
 *
 * Session restore flow (on every page load)
 * ──────────────────────────────────────────
 *   1. Read stored user from localStorage (instant — no API call)
 *   2. Render immediately with the cached data (fast UI)
 *   3. Call GET /auth/me to verify the token is still valid
 *   4a. Valid → update user with the fresh server data
 *   4b. Invalid → clear storage (interceptor already redirected to /login)
 *   setLoading(false) in both cases
 *
 * Why store user in localStorage?
 * ─────────────────────────────────
 *   On a hard refresh the React tree is rebuilt from scratch.
 *   Without a cached user the sidebar and navbar would flash empty
 *   for the duration of the /auth/me round-trip.  The cached object
 *   is shown instantly while the fresh data loads in the background.
 *
 * Usage
 * ──────
 *   import { useAuth } from "../context/AuthContext";
 *   const { user, login, logout, isAdmin } = useAuth();
 *
 *   Or via the convenience hook:
 *   import { useAuth } from "../hooks/useAuth";
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { useRouter } from "next/router";   // Pages Router
import toast from "react-hot-toast";
import { authService, User } from "../services/authService";
import { TokenStorage }      from "../services/api";

// ── Context type ─────────────────────────────────────────────────────────────

interface AuthContextType {
  /** Authenticated user, or null if not logged in */
  user: User | null;

  /** True while the session is being restored — show a spinner */
  isLoading: boolean;

  /**
   * Log in with email + password.
   * Stores tokens, updates user state, navigates to /dashboard.
   * Throws an AxiosError on bad credentials (catch in your form).
   */
  login: (email: string, password: string) => Promise<void>;

  /**
   * Log out the current user.
   * Clears all tokens from localStorage and navigates to /login.
   */
  logout: () => void;

  /** Returns true if the current user has the admin role. */
  isAdmin: () => boolean;

  /** Returns true if the current user has the ai_engineer role. */
  isAIEngineer: () => boolean;

  /**
   * Returns true if the current user has the analyst role.
   * Note: admins and ai_engineers can also access analyst features
   * (the server uses role-based guards, not hierarchy).
   */
  isAnalyst: () => boolean;
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * Access the auth context from any component.
 * Must be rendered inside <AuthProvider>.
 */
export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error(
      "useAuth() was called outside of <AuthProvider>. " +
      "Wrap your component tree with <AuthProvider> in _app.tsx.",
    );
  }
  return ctx;
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();

  const [user,      setUser]    = useState<User | null>(null);
  const [isLoading, setLoading] = useState<boolean>(true);

  // ── Session restore on mount ───────────────────────────────────────────────
  useEffect(() => {
    const restore = async () => {
      const stored = authService.getStoredUser();
      const token  = TokenStorage.getAccess();

      // No stored session → nothing to restore
      if (!stored || !token) {
        setLoading(false);
        return;
      }

      // Show cached data immediately so the UI doesn't flash empty
      setUser(stored);

      try {
        // Verify token is still valid with the server
        const fresh = await authService.getMe();
        setUser(fresh);
        // Update the cache with the latest server data
        TokenStorage.setUser(fresh);
      } catch {
        // Token invalid or expired — interceptor handles redirect to /login
        setUser(null);
        TokenStorage.clear();
      } finally {
        setLoading(false);
      }
    };

    restore();
    // Only run once on mount — empty dep array is intentional
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── login ─────────────────────────────────────────────────────────────────
  const login = useCallback(
    async (email: string, password: string): Promise<void> => {
      // authService.login() stores the tokens and returns TokenResponse
      const response = await authService.login(email, password);
      setUser(response.user);
      toast.success(
        `Welcome back, ${response.user.full_name.split(" ")[0]}!`,
      );
      router.push("/dashboard");
    },
    [router],
  );

  // ── logout ────────────────────────────────────────────────────────────────
  const logout = useCallback((): void => {
    authService.logout();
    setUser(null);
    toast.success("Logged out successfully.");
    router.push("/login");
  }, [router]);

  // ── Role helpers ──────────────────────────────────────────────────────────
  const isAdmin      = useCallback(() => user?.role === "admin",       [user]);
  const isAIEngineer = useCallback(() => user?.role === "ai_engineer", [user]);
  const isAnalyst    = useCallback(() => user?.role === "analyst",     [user]);

  // ── Context value ─────────────────────────────────────────────────────────
  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    isAdmin,
    isAIEngineer,
    isAnalyst,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}