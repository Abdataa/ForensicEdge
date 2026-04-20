/**
 * src/pages/login.tsx
 * ─────────────────────
 * Login page — email + password sign-in form.
 *
 * Access
 * ───────
 * Public — no auth required.
 * If the user is already authenticated and visits /login, they are
 * redirected to /dashboard immediately to avoid showing a redundant form.
 *
 * Form behaviour
 * ───────────────
 *   Submit calls AuthContext.login(email, password)
 *   On success: AuthContext navigates to /dashboard + shows welcome toast
 *   On failure: error message shown inline above the form fields
 *
 * Security notes
 * ───────────────
 *   - No "Register" link — account creation is admin-only
 *   - Password field has show/hide toggle for usability
 *   - Generic error message ("Invalid email or password") — does not
 *     reveal whether the email exists (prevents enumeration attacks)
 *   - Submit button is disabled while loading to prevent double-submit
 */

import { useState, FormEvent, useEffect } from "react";
import { useRouter }  from "next/router";
import Head           from "next/head";
import { Eye, EyeOff, Shield } from "lucide-react";
import { useAuth }    from "../hooks/useAuth";
import Button         from "../components/ui/Button";
import Input          from "../components/ui/Input";

export default function LoginPage() {
  const { login, user, isLoading } = useAuth();
  const router                      = useRouter();

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  // Redirect already-authenticated users away from login
  useEffect(() => {
    if (!isLoading && user) router.replace("/dashboard");
  }, [user, isLoading, router]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email.trim(), password);
      // AuthContext.login() handles the /dashboard redirect on success
    } catch (err: unknown) {
      // Surface the backend detail message if available, else use generic text
      const detail = (
        err as { response?: { data?: { detail?: string } } }
      )?.response?.data?.detail;
      setError(detail ?? "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  // Show nothing while redirecting authenticated users
  if (!isLoading && user) return null;

  return (
    <>
      <Head>
        <title>Sign In — ForensicEdge</title>
      </Head>

      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-8">

          {/* ── Logo + branding ─────────────────────────────────────────── */}
          <div className="text-center space-y-3">
            <div className="inline-flex items-center justify-center
                            w-16 h-16 rounded-2xl bg-blue-600 mx-auto">
              <Shield size={28} className="text-white" />
            </div>
            <div>
              <h1 className="text-white text-2xl font-bold tracking-tight">
                ForensicEdge
              </h1>
              <p className="text-gray-500 text-sm mt-1">
                AI-Assisted Evidence Analysis System
              </p>
            </div>
          </div>

          {/* ── Sign-in card ─────────────────────────────────────────────── */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-5">
            <h2 className="text-white font-semibold text-lg">Sign in</h2>

            {/* Inline error banner */}
            {error && (
              <div
                role="alert"
                className="bg-red-950 border border-red-800 rounded-xl
                           px-4 py-3 text-red-400 text-sm"
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-4">

              {/* Email */}
              <Input
                label="Email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@forensicedge.et"
                autoComplete="email"
                required
                disabled={loading}
              />

              {/* Password */}
              <Input
                label="Password"
                type={showPass ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                disabled={loading}
                suffix={
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPass((v) => !v)}
                    aria-label={showPass ? "Hide password" : "Show password"}
                    className="text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
              />

              {/* Submit */}
              <Button
                type="submit"
                fullWidth
                loading={loading}
              >
                {loading ? "Signing in…" : "Sign in"}
              </Button>

            </form>

            {/* Access notice — no Register link */}
            <p className="text-center text-gray-600 text-xs leading-relaxed">
              Access is restricted to authorised personnel only.
              <br />
              Contact your administrator to request an account.
            </p>
          </div>

        </div>
      </div>
    </>
  );
}