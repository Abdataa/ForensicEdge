/**
 * src/pages/profile.tsx
 * ──────────────────────
 * User profile management page — accessible to all authenticated roles.
 *
 * Sections
 * ─────────
 *   1. Profile info  — edit full_name and email  (PATCH /auth/me)
 *   2. Password      — change password            (POST /auth/change-password)
 *   3. Account info  — read-only: role, status, joined date, user ID
 *
 * API
 * ───
 *   GET    /auth/me              — pre-populate form fields (via useAuth)
 *   PATCH  /auth/me              — update full_name / email
 *   POST   /auth/change-password — current_password + new_password
 *
 * Backend schemas (from routes_auth.py)
 * ──────────────────────────────────────
 *   UpdateMyProfileRequest  { full_name?: str, email?: str }
 *   ChangePasswordRequest   { current_password: str, new_password: str }
 */

import { useState, FormEvent, useEffect } from "react";
import Head     from "next/head";
import {
  UserCircle2, Mail, KeyRound, CheckCircle,
  Save, Eye, EyeOff, Info, ShieldCheck,
} from "lucide-react";
import toast from "react-hot-toast";

import AppLayout  from "../components/layout/AppLayout";
import Card       from "../components/ui/Card";
import Button     from "../components/ui/Button";
import Input      from "../components/ui/Input";
import { RoleBadge, ActiveBadge } from "../components/ui/Badge";
import { useAuth } from "../hooks/useAuth";
import api         from "../services/api";

// ─────────────────────────────────────────────────────────────────────────────
// Password strength helper
// ─────────────────────────────────────────────────────────────────────────────

interface StrengthResult {
  score:  0 | 1 | 2 | 3 | 4;
  label:  string;
  color:  string;
  checks: { label: string; ok: boolean }[];
}

function checkStrength(pw: string): StrengthResult {
  const checks = [
    { label: "At least 8 characters",     ok: pw.length >= 8 },
    { label: "Uppercase letter (A–Z)",     ok: /[A-Z]/.test(pw) },
    { label: "Lowercase letter (a–z)",     ok: /[a-z]/.test(pw) },
    { label: "Number (0–9)",               ok: /[0-9]/.test(pw) },
    { label: "Special character (!@#…)",   ok: /[^A-Za-z0-9]/.test(pw) },
  ];
  const score = checks.filter((c) => c.ok).length as 0 | 1 | 2 | 3 | 4;
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const colors = ["", "text-red-400", "text-yellow-400", "text-blue-400", "text-green-400"];
  return { score, label: labels[score] ?? "", color: colors[score] ?? "", checks };
}

function StrengthBar({ score }: { score: number }) {
  const segments = 4;
  const filled   = Math.min(score, segments);
  const barColor = score <= 1 ? "bg-red-500" : score === 2 ? "bg-yellow-500" : score === 3 ? "bg-blue-500" : "bg-green-500";

  return (
    <div className="flex gap-1">
      {Array.from({ length: segments }).map((_, i) => (
        <div
          key={i}
          className={`h-1 flex-1 rounded-full transition-all duration-300 ${i < filled ? barColor : "bg-gray-800"}`}
        />
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Password field with show/hide toggle
// ─────────────────────────────────────────────────────────────────────────────

function PasswordInput({
  label,
  value,
  onChange,
  placeholder,
  disabled,
  autoComplete,
}: {
  label:        string;
  value:        string;
  onChange:     (v: string) => void;
  placeholder?: string;
  disabled?:    boolean;
  autoComplete?: string;
}) {
  const [show, setShow] = useState(false);

  return (
    <div className="space-y-1.5">
      <label className="field-label">{label}</label>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={autoComplete ?? "new-password"}
          className="field pr-10"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          disabled={disabled}
          className="absolute inset-y-0 right-3 flex items-center text-gray-500 hover:text-gray-300 transition-colors"
          tabIndex={-1}
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 1 — Profile info
// ─────────────────────────────────────────────────────────────────────────────

function ProfileInfoSection() {
  const { user, refreshUser } = useAuth();   // refreshUser re-fetches /auth/me and
                                              // updates the context after a successful PATCH

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email,    setEmail]    = useState(user?.email    ?? "");
  const [saving,   setSaving]   = useState(false);
  const [success,  setSuccess]  = useState(false);

  // Keep fields in sync if user object updates (e.g. after refresh)
  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setEmail(user?.email ?? "");
  }, [user?.full_name, user?.email]);

  const isDirty =
    fullName.trim() !== (user?.full_name ?? "") ||
    email.trim()    !== (user?.email    ?? "");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!isDirty) return;

    setSaving(true);
    setSuccess(false);

    // Only send fields that actually changed
    const payload: Record<string, string> = {};
    if (fullName.trim() !== user?.full_name) payload.full_name = fullName.trim();
    if (email.trim()    !== user?.email)     payload.email     = email.trim();

    try {
      await api.patch("/auth/me", payload);
      toast.success("Profile updated.");
      setSuccess(true);
      // Refresh the auth context so the navbar / profile card reflect the new name
      if (typeof refreshUser === "function") await refreshUser();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Update failed.";
      toast.error(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="Profile information">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Avatar + name row */}
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-950 flex items-center justify-center shrink-0">
            <UserCircle2 size={30} className="text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white font-medium truncate">{user?.full_name}</p>
            <p className="text-gray-500 text-xs mt-0.5 truncate">{user?.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Full name"
            value={fullName}
            onChange={(e) => { setFullName(e.target.value); setSuccess(false); }}
            placeholder="Abebe Girma"
            required
            minLength={2}
            maxLength={120}
            disabled={saving}
          />
          <div className="space-y-1.5">
            <label className="field-label">Email address</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-gray-600">
                <Mail size={14} />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setSuccess(false); }}
                placeholder="abebe@forensicedge.et"
                required
                disabled={saving}
                className="field pl-8"
              />
            </div>
          </div>
        </div>

        {/* Read-only note */}
        <div className="flex items-start gap-2 text-xs text-gray-600 bg-gray-900 rounded-xl px-3 py-2.5">
          <Info size={12} className="shrink-0 mt-0.5" />
          <span>
            Role and account status can only be changed by an administrator.
            To update your password, use the section below.
          </span>
        </div>

        {/* Success indicator */}
        {success && (
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <CheckCircle size={15} />
            Profile saved successfully.
          </div>
        )}

        <div className="flex items-center gap-3">
          <Button
            type="submit"
            loading={saving}
            disabled={!isDirty}
            icon={<Save size={14} />}
          >
            {saving ? "Saving…" : "Save changes"}
          </Button>
          {isDirty && !saving && (
            <Button
              type="button"
              variant="secondary"
              onClick={() => { setFullName(user?.full_name ?? ""); setEmail(user?.email ?? ""); setSuccess(false); }}
            >
              Discard
            </Button>
          )}
        </div>
      </form>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 2 — Change password
// ─────────────────────────────────────────────────────────────────────────────

function ChangePasswordSection() {
  const [currentPw, setCurrentPw] = useState("");
  const [newPw,     setNewPw]     = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [saving,    setSaving]    = useState(false);
  const [success,   setSuccess]   = useState(false);

  const strength   = checkStrength(newPw);
  const mismatch   = confirmPw.length > 0 && newPw !== confirmPw;
  const canSubmit  = currentPw.length > 0 && newPw.length >= 8 && newPw === confirmPw;

  const reset = () => {
    setCurrentPw("");
    setNewPw("");
    setConfirmPw("");
    setSuccess(false);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSaving(true);
    setSuccess(false);

    try {
      await api.post("/auth/change-password", {
        current_password: currentPw,
        new_password:     newPw,
      });
      toast.success("Password changed successfully.");
      setSuccess(true);
      reset();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Password change failed.";
      toast.error(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="Change password">
      <form onSubmit={handleSubmit} className="space-y-5">
        <PasswordInput
          label="Current password"
          value={currentPw}
          onChange={(v) => { setCurrentPw(v); setSuccess(false); }}
          placeholder="Your existing password"
          disabled={saving}
          autoComplete="current-password"
        />

        <div className="space-y-2">
          <PasswordInput
            label="New password"
            value={newPw}
            onChange={(v) => { setNewPw(v); setSuccess(false); }}
            placeholder="Min 8 chars, uppercase + digit"
            disabled={saving}
            autoComplete="new-password"
          />

          {/* Strength bar + label */}
          {newPw.length > 0 && (
            <div className="space-y-1.5">
              <StrengthBar score={strength.score} />
              <div className="flex items-center justify-between">
                <span className={`text-xs font-medium ${strength.color}`}>
                  {strength.label}
                </span>
                <div className="flex gap-3 flex-wrap justify-end">
                  {strength.checks.map((c) => (
                    <span
                      key={c.label}
                      className={`text-xs flex items-center gap-1 ${c.ok ? "text-green-500" : "text-gray-600"}`}
                    >
                      <CheckCircle size={10} />
                      {c.label}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-1.5">
          <PasswordInput
            label="Confirm new password"
            value={confirmPw}
            onChange={(v) => { setConfirmPw(v); setSuccess(false); }}
            placeholder="Re-enter new password"
            disabled={saving}
            autoComplete="new-password"
          />
          {mismatch && (
            <p className="text-xs text-red-400">Passwords do not match.</p>
          )}
        </div>

        {/* Success indicator */}
        {success && (
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <CheckCircle size={15} />
            Password changed. Use the new password at your next login.
          </div>
        )}

        <Button
          type="submit"
          loading={saving}
          disabled={!canSubmit}
          icon={<KeyRound size={14} />}
        >
          {saving ? "Changing…" : "Change password"}
        </Button>
      </form>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 3 — Account info (read-only)
// ─────────────────────────────────────────────────────────────────────────────

function AccountInfoSection() {
  const { user } = useAuth();
  if (!user) return null;

  const rows = [
    { label: "User ID",   value: `#${user.id}`,   mono: true  },
    { label: "Role",      value: <RoleBadge role={user.role} />,     mono: false },
    { label: "Status",    value: <ActiveBadge isActive={user.is_active} />, mono: false },
    {
      label: "Member since",
      value: new Date(user.created_at).toLocaleDateString(undefined, {
        month: "long", day: "numeric", year: "numeric",
      }),
      mono: false,
    },
  ];

  return (
    <Card title="Account information">
      <div className="flex items-center gap-2 mb-4 text-xs text-gray-600 bg-gray-900 rounded-xl px-3 py-2.5">
        <ShieldCheck size={12} className="shrink-0" />
        <span>These fields are managed by your administrator and cannot be changed here.</span>
      </div>

      <dl className="divide-y divide-gray-800">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between py-3 gap-4">
            <dt className="text-sm text-gray-500 shrink-0">{row.label}</dt>
            <dd className={`text-sm text-right ${row.mono ? "font-mono text-gray-300" : "text-white"}`}>
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  return (
    <>
      <Head><title>Profile — ForensicEdge</title></Head>

      <AppLayout title="My Profile">
        <div className="max-w-2xl space-y-5">
          <ProfileInfoSection />
          <ChangePasswordSection />
          <AccountInfoSection />
        </div>
      </AppLayout>
    </>
  );
}