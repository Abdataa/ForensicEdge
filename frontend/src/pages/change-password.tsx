/**
 * src/pages/change-password.tsx
 * ───────────────────────────────
 * Password change page — available to every authenticated user.
 *
 * Primary use case
 * ─────────────────
 * When an admin creates a new account they set a temporary password.
 * The user logs in with that password and is expected to change it
 * here immediately.  There is no forced redirect — the sidebar
 * always shows the "Password" link so users can find it easily.
 *
 * Validation (client-side, mirrors backend rules)
 * ─────────────────────────────────────────────────
 *   new password must be ≥ 8 characters
 *   must contain at least one uppercase letter
 *   must contain at least one digit
 *   confirm password must match new password
 *
 * The backend also validates — the client check is for immediate UX.
 */

import { useState, FormEvent } from "react";
import Head  from "next/head";
import { KeyRound, Eye, EyeOff, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";

import AppLayout from "../components/layout/AppLayout";
import Card      from "../components/ui/Card";
import Input     from "../components/ui/Input";
import Button    from "../components/ui/Button";
import { authService } from "../services/authService";

export default function ChangePasswordPage() {
  const [current,   setCurrent]   = useState("");
  const [next,      setNext]      = useState("");
  const [confirm,   setConfirm]   = useState("");
  const [showCurr,  setShowCurr]  = useState(false);
  const [showNext,  setShowNext]  = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");
  const [success,   setSuccess]   = useState(false);

  // ── Client-side validation ────────────────────────────────────────────────
  const validate = (): string => {
    if (!current.trim())
      return "Please enter your current password.";
    if (next.length < 8)
      return "New password must be at least 8 characters.";
    if (!/[A-Z]/.test(next))
      return "New password must contain at least one uppercase letter.";
    if (!/[0-9]/.test(next))
      return "New password must contain at least one digit.";
    if (next !== confirm)
      return "New password and confirmation do not match.";
    if (next === current)
      return "New password must be different from the current password.";
    return "";
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      await authService.changePassword(current, next);
      setSuccess(true);
      toast.success("Password changed successfully.");
      // Clear all fields after success
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Failed to change password. Please try again.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head><title>Change Password — ForensicEdge</title></Head>

      <AppLayout title="Change Password">

        <div className="max-w-md space-y-4">

          {/* ── Success state ──────────────────────────────────────────── */}
          {success && (
            <div className="flex items-start gap-3 bg-green-950 border border-green-800
                            rounded-xl px-4 py-4 text-green-300">
              <CheckCircle size={18} className="shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-sm">Password changed successfully.</p>
                <p className="text-green-400/70 text-xs mt-0.5">
                  Your new password is active immediately.
                </p>
              </div>
            </div>
          )}

          {/* ── Form card ─────────────────────────────────────────────── */}
          <Card title="Change Password">

            <p className="text-gray-500 text-sm mb-5 leading-relaxed">
              Enter your current password (or the temporary password set by your
              administrator), then choose a new password.
            </p>

            {/* Error banner */}
            {error && (
              <div className="bg-red-950 border border-red-800 rounded-xl
                              px-4 py-3 text-red-400 text-sm mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-4">

              {/* Current password */}
              <Input
                label="Current password"
                type={showCurr ? "text" : "password"}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                placeholder="Your current or temporary password"
                autoComplete="current-password"
                required
                disabled={loading}
                suffix={
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowCurr((v) => !v)}
                    aria-label={showCurr ? "Hide password" : "Show password"}
                    className="text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showCurr ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
              />

              {/* New password */}
              <Input
                label="New password"
                type={showNext ? "text" : "password"}
                value={next}
                onChange={(e) => setNext(e.target.value)}
                placeholder="Min 8 chars, uppercase + digit"
                autoComplete="new-password"
                required
                minLength={8}
                disabled={loading}
                suffix={
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowNext((v) => !v)}
                    aria-label={showNext ? "Hide password" : "Show password"}
                    className="text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showNext ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
              />

              {/* Confirm new password */}
              <Input
                label="Confirm new password"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Repeat new password"
                autoComplete="new-password"
                required
                disabled={loading}
                error={
                  confirm.length > 0 && confirm !== next
                    ? "Passwords do not match."
                    : undefined
                }
              />

              {/* Password requirements hint */}
              <ul className="text-gray-600 text-xs space-y-1 list-none">
                <PasswordHint met={next.length >= 8}         text="At least 8 characters" />
                <PasswordHint met={/[A-Z]/.test(next)}       text="At least one uppercase letter" />
                <PasswordHint met={/[0-9]/.test(next)}       text="At least one digit" />
                <PasswordHint met={next === confirm && next.length > 0} text="Passwords match" />
              </ul>

              <Button
                type="submit"
                fullWidth
                loading={loading}
              >
                {loading ? "Saving…" : "Save new password"}
              </Button>

            </form>
          </Card>

        </div>

      </AppLayout>
    </>
  );
}

// ── Password hint row ─────────────────────────────────────────────────────────

function PasswordHint({ met, text }: { met: boolean; text: string }) {
  return (
    <li className="flex items-center gap-2">
      <span className={met ? "text-green-400" : "text-gray-700"}>
        {met ? "✓" : "○"}
      </span>
      <span className={met ? "text-green-400" : "text-gray-600"}>
        {text}
      </span>
    </li>
  );
}