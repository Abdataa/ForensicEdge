/**
 * src/services/authService.ts
 * ────────────────────────────
 * All authentication-related API calls.
 *
 * Backend endpoints consumed
 * ───────────────────────────
 *   POST /api/v1/auth/login           → TokenResponse
 *   GET  /api/v1/auth/me              → UserResponse
 *   POST /api/v1/auth/refresh         → AccessTokenResponse
 *   POST /api/v1/auth/change-password → { message }
 *
 * Note: POST /auth/register has been removed from the backend.
 *       Accounts are created exclusively by an admin via
 *       POST /admin/users.  There is no public sign-up.
 */

import api, { TokenStorage } from "./api";

// ── Types that mirror the backend Pydantic schemas ───────────────────────────

/** Matches UserResponse in backend/app/schemas/user_schema.py */
export interface User {
  id:         number;
  full_name:  string;
  email:      string;
  role:       "analyst" | "admin" | "ai_engineer";
  is_active:  boolean;
  created_at: string;   // ISO datetime string
  updated_at: string;
}

/** Matches TokenResponse */
export interface TokenResponse {
  access_token:  string;
  refresh_token: string;
  token_type:    string;   // always "bearer"
  user:          User;
}

/** Matches AccessTokenResponse (refresh endpoint) */
export interface AccessTokenResponse {
  access_token: string;
  token_type:   string;
}

// ── Service ──────────────────────────────────────────────────────────────────

export const authService = {

  /**
   * POST /api/v1/auth/login
   * Authenticates with email + password.
   * Stores both tokens and the User object in localStorage.
   * Called by AuthContext.login().
   */
  async login(email: string, password: string): Promise<TokenResponse> {
    const { data } = await api.post<TokenResponse>("/auth/login", {
      email,
      password,
    });

    // Persist tokens for the Axios interceptor
    TokenStorage.setAccess(data.access_token);
    TokenStorage.setRefresh(data.refresh_token);
    // Cache user so session can be restored without an extra API call
    TokenStorage.setUser(data.user);

    return data;
  },

  /**
   * GET /api/v1/auth/me
   * Returns the current user's profile.
   * Called on app mount to verify the stored token is still valid.
   */
  async getMe(): Promise<User> {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },

  /**
   * POST /api/v1/auth/change-password
   * Changes the authenticated user's password.
   * Body: { current_password, new_password }
   * Used on the /change-password page and essential for first-login
   * users who received a temporary password from the admin.
   */
  async changePassword(
    currentPassword: string,
    newPassword:     string,
  ): Promise<void> {
    await api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password:     newPassword,
    });
  },

  /**
   * Clears all tokens and cached user data from localStorage.
   * The backend JWT expires naturally — no server-side logout call needed.
   * Called by AuthContext.logout().
   */
  logout(): void {
    TokenStorage.clear();
  },

  /**
   * Reads the cached User object from localStorage.
   * Returns null if no session exists or code runs server-side.
   * Used by AuthContext on mount for an instant (non-blocking) UI restore.
   */
  getStoredUser(): User | null {
    const raw = TokenStorage.getUser();
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  },
};