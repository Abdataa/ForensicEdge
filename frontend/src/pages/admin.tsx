/**
 * src/pages/admin.tsx
 * ─────────────────────
 * User management page — admin only.
 *
 * Features
 * ─────────
 *   List all users with role + status badges
 *   Create new user (inline form — admin sets name, email, temp password, role)
 *   Activate / deactivate user account (PATCH /admin/users/{id})
 *   Delete user permanently (DELETE /admin/users/{id})
 *
 * Security note
 * ──────────────
 *   requiredRole="admin" on AppLayout redirects non-admins to /dashboard
 *   before this component renders. The server enforces the same rules.
 *
 * Create user flow
 * ─────────────────
 *   Admin fills in the form and submits.
 *   Backend creates the account with the given temporary password.
 *   User logs in with that password then uses /change-password to set their own.
 */

import { useState, useEffect, FormEvent } from "react";
import Head from "next/head";
import { Plus, Trash2, UserX, UserCheck, Users, ChevronDown, ChevronUp } from "lucide-react";
import toast from "react-hot-toast";
import clsx  from "clsx";

import AppLayout from "../components/layout/AppLayout";
import Card      from "../components/ui/Card";
import Button    from "../components/ui/Button";
import Input     from "../components/ui/Input";
import { RoleBadge, ActiveBadge } from "../components/ui/Badge";
import Spinner   from "../components/ui/Spinner";
import api       from "../services/api";
import { User }  from "../services/authService";

// ── Types ────────────────────────────────────────────────────────────────────

interface UserListResponse {
  total: number;
  users: User[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [users,     setUsers]     = useState<User[]>([]);
  const [total,     setTotal]     = useState(0);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  // Create user form state
  const [fullName,   setFullName]   = useState("");
  const [email,      setEmail]      = useState("");
  const [password,   setPassword]   = useState("");
  const [role,       setRole]       = useState<User["role"]>("analyst");
  const [creating,   setCreating]   = useState(false);
  const [formError,  setFormError]  = useState("");

  const loadUsers = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<UserListResponse>("/admin/users", {
        params: { limit: 100 },
      });
      setUsers(data.users);
      setTotal(data.total);
    } catch {
      toast.error("Could not load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadUsers(); }, []);

  // ── Activate / deactivate ─────────────────────────────────────────────────
  const handleToggleActive = async (user: User) => {
    setTogglingId(user.id);
    try {
      await api.patch(`/admin/users/${user.id}`, {
        is_active: !user.is_active,
      });
      const action = user.is_active ? "deactivated" : "activated";
      toast.success(`${user.full_name} ${action}.`);
      await loadUsers();
    } catch {
      toast.error("Update failed.");
    } finally {
      setTogglingId(null);
    }
  };

  // ── Delete ────────────────────────────────────────────────────────────────
  const handleDelete = async (user: User) => {
    if (!confirm(
      `Permanently delete "${user.full_name}"?\n\n` +
      `This will remove their account and all associated data. ` +
      `This action cannot be undone.`
    )) return;

    setDeletingId(user.id);
    try {
      await api.delete(`/admin/users/${user.id}`);
      toast.success("User deleted.");
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
      setTotal((t) => t - 1);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Delete failed.";
      toast.error(detail);
    } finally {
      setDeletingId(null);
    }
  };

  // ── Create user ───────────────────────────────────────────────────────────
  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setFormError("");
    setCreating(true);
    try {
      await api.post("/admin/users", {
        full_name: fullName.trim(),
        email:     email.trim(),
        password,
        role,
      });
      toast.success(`User "${fullName}" created.`);
      // Reset form
      setFullName(""); setEmail(""); setPassword(""); setRole("analyst");
      setShowForm(false);
      await loadUsers();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Creation failed.";
      setFormError(detail);
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <Head><title>User Management — ForensicEdge</title></Head>

      {/* Admin-only — non-admins are redirected to /dashboard by AppLayout */}
      <AppLayout title="User Management" requiredRole="admin">

        {/* ── Header ────────────────────────────────────────────────────── */}
        <div className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-white font-semibold text-lg">Users</h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {loading ? "Loading…" : `${total} registered user${total !== 1 ? "s" : ""}`}
            </p>
          </div>

          <Button
            size="sm"
            icon={showForm ? <ChevronUp size={14} /> : <Plus size={14} />}
            onClick={() => { setShowForm((v) => !v); setFormError(""); }}
          >
            {showForm ? "Cancel" : "Add user"}
          </Button>
        </div>

        {/* ── Create user form ──────────────────────────────────────────── */}
        {showForm && (
          <Card title="Create new user">

            {formError && (
              <div className="bg-red-950 border border-red-800 rounded-xl
                              px-4 py-3 text-red-400 text-sm mb-2">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Abebe Girma"
                  required
                  minLength={2}
                  disabled={creating}
                />
                <Input
                  label="Email address"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="abebe@forensicedge.et"
                  required
                  disabled={creating}
                />
                <Input
                  label="Temporary password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 chars, uppercase + digit"
                  required
                  minLength={8}
                  disabled={creating}
                />
                <div className="space-y-1.5">
                  <label  htmlFor="role"   className="field-label">Role</label>
                  <select
                    id = "role"
                    value={role}
                    onChange={(e) => setRole(e.target.value as User["role"])}
                    disabled={creating}
                    className="field"
                  >
                    <option value="analyst">Analyst</option>
                    <option value="admin">Admin</option>
                    <option value="ai_engineer">AI Engineer</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button type="submit" loading={creating}>
                  Create user
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => { setShowForm(false); setFormError(""); }}
                  disabled={creating}
                >
                  Cancel
                </Button>
              </div>

              <p className="text-gray-600 text-xs">
                The user will log in with this temporary password and should
                change it immediately via <strong className="text-gray-500">
                Settings → Password</strong>.
              </p>
            </form>
          </Card>
        )}

        {/* ── Users table ───────────────────────────────────────────────── */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>

        ) : users.length === 0 ? (
          <Card className="text-center py-12 space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center
                            justify-center mx-auto">
              <Users size={24} className="text-gray-600" />
            </div>
            <p className="text-gray-500 text-sm">No users found.</p>
          </Card>

        ) : (
          <Card padding="p-0">
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th className="whitespace-nowrap">Joined</th>
                    <th className="w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      {/* Name */}
                      <td>
                        <span className="text-white font-medium">
                          {user.full_name}
                        </span>
                      </td>

                      {/* Email */}
                      <td className="text-gray-400 text-sm">
                        {user.email}
                      </td>

                      {/* Role badge */}
                      <td>
                        <RoleBadge role={user.role} />
                      </td>

                      {/* Active badge */}
                      <td>
                        <ActiveBadge isActive={user.is_active} />
                      </td>

                      {/* Joined date */}
                      <td className="text-gray-500 text-xs whitespace-nowrap">
                        {new Date(user.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day:   "numeric",
                          year:  "numeric",
                        })}
                      </td>

                      {/* Actions */}
                      <td>
                        <div className="flex items-center gap-1">
                          {/* Activate / Deactivate */}
                          <button
                            onClick={() => handleToggleActive(user)}
                            disabled={togglingId === user.id}
                            title={user.is_active ? "Deactivate account" : "Activate account"}
                            className={clsx(
                              "p-1.5 rounded-lg transition-colors",
                              "text-gray-500 hover:bg-gray-800",
                              user.is_active
                                ? "hover:text-yellow-400"
                                : "hover:text-green-400",
                            )}
                          >
                            {togglingId === user.id
                              ? <Spinner size="sm" />
                              : user.is_active
                                ? <UserX    size={15} />
                                : <UserCheck size={15} />
                            }
                          </button>

                          {/* Delete */}
                          <button
                            onClick={() => handleDelete(user)}
                            disabled={deletingId === user.id}
                            title="Delete user permanently"
                            className="p-1.5 rounded-lg text-gray-500
                                       hover:text-red-400 hover:bg-gray-800
                                       transition-colors"
                          >
                            {deletingId === user.id
                              ? <Spinner size="sm" />
                              : <Trash2 size={15} />
                            }
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

      </AppLayout>
    </>
  );
}