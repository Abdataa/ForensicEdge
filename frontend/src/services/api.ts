/**
 * src/services/api.ts
 * ────────────────────
 * Axios base instance shared by every service file.
 *
 * Responsibilities
 * ─────────────────
 * 1. Reads NEXT_PUBLIC_API_URL and sets baseURL to /api/v1
 * 2. Attaches the stored access token as Bearer on every request
 * 3. On a 401 response:
 *      a. Uses the stored refresh token to call POST /auth/refresh
 *      b. Stores the new access token and retries the original request
 *      c. Queues any parallel requests until the refresh completes
 *      d. If refresh fails → clears storage and redirects to /login
 *
 * Token storage
 * ─────────────
 * Keys use a "fe_" prefix to avoid clashing with other apps on the
 * same localhost during development.
 *   fe_access   — short-lived JWT (60 min)
 *   fe_refresh  — long-lived JWT  (7 days)
 *   fe_user     — cached User object (JSON string)
 */

import axios, {
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

// ── Base URL ────────────────────────────────────────────────────────────────
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Token helpers ────────────────────────────────────────────────────────────
const isClient = typeof window !== "undefined";

export const TokenStorage = {
  getAccess:  (): string | null  => isClient ? localStorage.getItem("fe_access")  : null,
  getRefresh: (): string | null  => isClient ? localStorage.getItem("fe_refresh") : null,
  setAccess:  (t: string): void  => localStorage.setItem("fe_access",  t),
  setRefresh: (t: string): void  => localStorage.setItem("fe_refresh", t),
  setUser:    (u: object): void  => localStorage.setItem("fe_user",    JSON.stringify(u)),
  getUser:    (): string | null  => isClient ? localStorage.getItem("fe_user") : null,
  clear: (): void => {
    ["fe_access", "fe_refresh", "fe_user"].forEach((k) =>
      localStorage.removeItem(k)
    );
  },
};

// ── Axios instance ───────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,                  // 30 s — AI inference can be slow
});

// ── Request interceptor — attach Bearer token ────────────────────────────────
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = TokenStorage.getAccess();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor — auto-refresh on 401 ───────────────────────────────
let _isRefreshing = false;
let _pendingQueue: Array<{
  resolve: (token: string) => void;
  reject:  (error: unknown) => void;
}> = [];

function _processQueue(error: unknown, token: string | null): void {
  _pendingQueue.forEach((p) =>
    error ? p.reject(error) : p.resolve(token!)
  );
  _pendingQueue = [];
}

api.interceptors.response.use(
  (response: AxiosResponse) => response,

  async (error) => {
    const originalRequest = error.config;

    // Only intercept 401s that haven't already been retried
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Never intercept login or refresh endpoints themselves
    const url: string = originalRequest.url ?? "";
    if (url.includes("/auth/login") || url.includes("/auth/refresh")) {
      return Promise.reject(error);
    }

    // If a refresh is already in-flight, queue this request
    if (_isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        _pendingQueue.push({ resolve, reject });
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    _isRefreshing           = true;

    const refreshToken = TokenStorage.getRefresh();
    if (!refreshToken) {
      TokenStorage.clear();
      if (isClient) window.location.href = "/login";
      return Promise.reject(error);
    }

    try {
      // POST /auth/refresh  — body: { refresh_token }
      // Returns: { access_token, token_type }
      const { data } = await axios.post(
        `${BASE_URL}/api/v1/auth/refresh`,
        { refresh_token: refreshToken },
      );

      const newAccessToken: string = data.access_token;
      TokenStorage.setAccess(newAccessToken);
      api.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`;

      _processQueue(null, newAccessToken);
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);

    } catch (refreshError) {
      _processQueue(refreshError, null);
      TokenStorage.clear();
      if (isClient) window.location.href = "/login";
      return Promise.reject(refreshError);

    } finally {
      _isRefreshing = false;
    }
  },
);

export default api;
