/**
 * src/pages/admin.tsx
 * ─────────────────────
 * Admin-only page with three tabs:
 *
 *   1. Users         — list / create / activate / deactivate / delete
 *   2. System health — GET /admin/health   (live service + resource status)
 *   3. Audit logs    — GET /admin/audit-logs?user_id=&action_type=&page=&limit=
 *
 * Security note
 * ──────────────
 *   requiredRole="admin" on AppLayout redirects non-admins to /dashboard
 *   before this component renders. The server enforces the same rules.
 */

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  FormEvent,
} from "react";
import Head from "next/head";
import {
  Plus,
  Trash2,
  UserX,
  UserCheck,
  Users,
  ChevronUp,
  Activity,
  ScrollText,
  RefreshCw,
} from "lucide-react";
import toast  from "react-hot-toast";
import clsx   from "clsx";

import AppLayout               from "../components/layout/AppLayout";
import Card                    from "../components/ui/Card";
import Button                  from "../components/ui/Button";
import Input                   from "../components/ui/Input";
import { RoleBadge, ActiveBadge } from "../components/ui/Badge";
import Spinner                 from "../components/ui/Spinner";
import api                     from "../services/api";
import { User }                from "../services/authService";

// ─────────────────────────────────────────────────────────────────────────────
// Shared types
// ─────────────────────────────────────────────────────────────────────────────

interface UserListResponse {
  total: number;
  users: User[];
}

// ── Health ──────────────────────────────────────────────────────────────────

type ServiceStatus = "ok" | "warn" | "error";

interface HealthService {
  name:        string;
  status:      ServiceStatus;
  latency_ms:  number | null;
  detail:      string;
}

interface HealthResource {
  name:   string;
  value:  string;
  pct:    number;
  status: ServiceStatus;
}

interface HealthData {
  status:    "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  metrics: {
    avg_response_ms:  number;
    requests_today:   number;
    active_sessions:  number;
    error_rate_pct:   number;
  };
  services:  HealthService[];
  resources: HealthResource[];
}

// ── Audit ────────────────────────────────────────────────────────────────────

interface AuditLog {
  id:          number;
  user_id:     number | null;
  action_type: string;
  details:     Record<string, unknown> | null;
  ip_address:  string | null;
  timestamp:   string;
}

interface AuditLogsResponse {
  logs:  AuditLog[];
  total: number;
  page:  number;
  limit: number;
  pages: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const AUDIT_ACTION_TYPES = [
  "image_uploaded",
  "comparison_completed",
  "report_generated",
  "user_login",
  "user_deleted",
  "admin_action",
] as const;

type ActionType = typeof AUDIT_ACTION_TYPES[number] | "";

const ACTION_BADGE_CLASSES: Record<string, string> = {
  image_uploaded:       "bg-blue-950  text-blue-400",
  comparison_completed: "bg-green-950 text-green-400",
  user_login:           "bg-purple-950 text-purple-400",
  report_generated:     "bg-yellow-950 text-yellow-400",
  user_deleted:         "bg-red-950   text-red-400",
  admin_action:         "bg-pink-950  text-pink-400",
};

const AUDIT_PER_PAGE = 15;

const STATUS_DOT: Record<ServiceStatus, string> = {
  ok:    "bg-green-500",
  warn:  "bg-yellow-500",
  error: "bg-red-500",
};

const STATUS_BADGE: Record<ServiceStatus, string> = {
  ok:    "bg-green-950  text-green-400",
  warn:  "bg-yellow-950 text-yellow-400",
  error: "bg-red-950    text-red-400",
};

// ─────────────────────────────────────────────────────────────────────────────
// Small sub-components (all private to this file)
// ─────────────────────────────────────────────────────────────────────────────

// ── Tab bar ──────────────────────────────────────────────────────────────────

type TabId = "users" | "health" | "audit";

interface TabDef { id: TabId; label: string; icon: React.ReactNode }

const TABS: TabDef[] = [
  { id: "users",  label: "Users",          icon: <Users     size={14} /> },
  { id: "health", label: "System health",  icon: <Activity  size={14} /> },
  { id: "audit",  label: "Audit logs",     icon: <ScrollText size={14} /> },
];

function TabBar({
  active,
  onChange,
}: {
  active: TabId;
  onChange: (id: TabId) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-gray-800 mb-6">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={clsx(
            "flex items-center gap-1.5 px-4 py-2.5 text-sm -mb-px border-b-2 transition-colors",
            active === t.id
              ? "border-white text-white font-medium"
              : "border-transparent text-gray-500 hover:text-gray-300"
          )}
        >
          {t.icon}
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ── Health helpers ───────────────────────────────────────────────────────────

function HealthMetricCard({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1.5">{label}</p>
      <p className={clsx("text-2xl font-semibold", ok ? "text-green-400" : "text-yellow-400")}>
        {value}
      </p>
    </div>
  );
}

function ServiceRow({ service }: { service: HealthService }) {
  return (
    <div className="flex items-center gap-3 bg-gray-900 rounded-xl px-4 py-3">
      <span className={clsx("w-2 h-2 rounded-full shrink-0", STATUS_DOT[service.status])} />
      <span className="text-sm font-medium text-white flex-1">{service.name}</span>
      <span className="text-xs text-gray-500">
        {service.latency_ms != null ? `${service.latency_ms}ms` : "—"}
      </span>
      <span className={clsx("text-xs px-2.5 py-0.5 rounded-full font-medium", STATUS_BADGE[service.status])}>
        {service.status === "ok" ? "Healthy" : service.status === "warn" ? "Warning" : "Error"}
      </span>
    </div>
  );
}

function ResourceRow({ resource }: { resource: HealthResource }) {
  const pct = Math.min(100, Math.max(0, resource.pct));
  const barColor = resource.status === "ok"
    ? "bg-green-500"
    : resource.status === "warn"
    ? "bg-yellow-500"
    : "bg-red-500";
  return (
    <div className="flex flex-col gap-1.5 bg-gray-900 rounded-xl px-4 py-3">
      <div className="flex items-center gap-2">
        <span className={clsx("w-2 h-2 rounded-full shrink-0", STATUS_DOT[resource.status])} />
        <span className="text-sm font-medium text-white flex-1">{resource.name}</span>
        <span className="text-sm font-medium text-white">{resource.value}</span>
      </div>
      <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-500", barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Audit helpers ────────────────────────────────────────────────────────────

function ActionBadge({ action }: { action: string }) {
  return (
    <span
      className={clsx(
        "inline-block text-xs px-2 py-0.5 rounded-full font-medium",
        ACTION_BADGE_CLASSES[action] ?? "bg-gray-800 text-gray-400"
      )}
    >
      {action}
    </span>
  );
}

function AuditPagination({
  page,
  pages,
  onChange,
}: {
  page: number;
  pages: number;
  onChange: (p: number) => void;
}) {
  if (pages <= 1) return null;
  const lo = Math.max(1, page - 2);
  const hi = Math.min(pages, page + 2);

  const btnCls = (active: boolean, disabled = false) =>
    clsx(
      "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
      active
        ? "border-gray-600 bg-gray-800 text-white"
        : "border-gray-800 text-gray-500 hover:text-white hover:border-gray-600",
      disabled && "opacity-40 pointer-events-none"
    );

  const items: React.ReactNode[] = [];

  items.push(
    <button key="prev" onClick={() => onChange(page - 1)} disabled={page === 1}
      className={btnCls(false, page === 1)}>← Prev</button>
  );

  if (lo > 1) {
    items.push(<button key="p1" onClick={() => onChange(1)} className={btnCls(false)}>1</button>);
    if (lo > 2) items.push(<span key="e1" className="text-gray-600 px-1">…</span>);
  }

  for (let i = lo; i <= hi; i++) {
    items.push(
      <button key={i} onClick={() => onChange(i)} className={btnCls(i === page)}>{i}</button>
    );
  }

  if (hi < pages) {
    if (hi < pages - 1) items.push(<span key="e2" className="text-gray-600 px-1">…</span>);
    items.push(<button key="last" onClick={() => onChange(pages)} className={btnCls(false)}>{pages}</button>);
  }

  items.push(
    <button key="next" onClick={() => onChange(page + 1)} disabled={page === pages}
      className={btnCls(false, page === pages)}>Next →</button>
  );

  return <div className="flex items-center gap-1">{items}</div>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main panel sections
// ─────────────────────────────────────────────────────────────────────────────

// ── 1. Users panel ───────────────────────────────────────────────────────────

function UsersPanel() {
  const [users,      setUsers]      = useState<User[]>([]);
  const [total,      setTotal]      = useState(0);
  const [loading,    setLoading]    = useState(true);
  const [showForm,   setShowForm]   = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const [fullName,  setFullName]  = useState("");
  const [email,     setEmail]     = useState("");
  const [password,  setPassword]  = useState("");
  const [role,      setRole]      = useState<User["role"]>("analyst");
  const [creating,  setCreating]  = useState(false);
  const [formError, setFormError] = useState("");

  const loadUsers = useCallback(async () => {
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
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleToggleActive = async (user: User) => {
    setTogglingId(user.id);
    try {
      await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active });
      toast.success(`${user.full_name} ${user.is_active ? "deactivated" : "activated"}.`);
      await loadUsers();
    } catch {
      toast.error("Update failed.");
    } finally {
      setTogglingId(null);
    }
  };

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
    <div className="space-y-5">
      {/* Header */}
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

      {/* Create form */}
      {showForm && (
        <Card title="Create new user">
          {formError && (
            <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm mb-2">
              {formError}
            </div>
          )}
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)}
                placeholder="Abebe Girma" required minLength={2} disabled={creating} />
              <Input label="Email address" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="abebe@forensicedge.et" required disabled={creating} />
              <Input label="Temporary password" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 chars, uppercase + digit" required minLength={8} disabled={creating} />
              <div className="space-y-1.5">
                <label htmlFor="role" className="field-label">Role</label>
                <select id="role" value={role} onChange={(e) => setRole(e.target.value as User["role"])}
                  disabled={creating} className="field">
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                  <option value="ai_engineer">AI Engineer</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" loading={creating}>Create user</Button>
              <Button type="button" variant="secondary"
                onClick={() => { setShowForm(false); setFormError(""); }} disabled={creating}>
                Cancel
              </Button>
            </div>
            <p className="text-gray-600 text-xs">
              The user will log in with this temporary password and should change it immediately via{" "}
              <strong className="text-gray-500">Settings → Password</strong>.
            </p>
          </form>
        </Card>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : users.length === 0 ? (
        <Card className="text-center py-12 space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
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
                    <td><span className="text-white font-medium">{user.full_name}</span></td>
                    <td className="text-gray-400 text-sm">{user.email}</td>
                    <td><RoleBadge role={user.role} /></td>
                    <td><ActiveBadge isActive={user.is_active} /></td>
                    <td className="text-gray-500 text-xs whitespace-nowrap">
                      {new Date(user.created_at).toLocaleDateString(undefined, {
                        month: "short", day: "numeric", year: "numeric",
                      })}
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={togglingId === user.id}
                          title={user.is_active ? "Deactivate account" : "Activate account"}
                          className={clsx(
                            "p-1.5 rounded-lg transition-colors text-gray-500 hover:bg-gray-800",
                            user.is_active ? "hover:text-yellow-400" : "hover:text-green-400"
                          )}
                        >
                          {togglingId === user.id ? <Spinner size="sm" />
                            : user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                        </button>
                        <button
                          onClick={() => handleDelete(user)}
                          disabled={deletingId === user.id}
                          title="Delete user permanently"
                          className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-gray-800 transition-colors"
                        >
                          {deletingId === user.id ? <Spinner size="sm" /> : <Trash2 size={15} />}
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
    </div>
  );
}

// ── 2. System Health panel ───────────────────────────────────────────────────

function SystemHealthPanel() {
  const [data,         setData]         = useState<HealthData | null>(null);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState<string | null>(null);
  const [lastChecked,  setLastChecked]  = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: json } = await api.get<HealthData>("/admin/health");
      setData(json);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Could not reach health endpoint.";
      setError(msg);
      toast.error("Health check failed.");
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const id = setInterval(fetchHealth, 60_000);
    return () => clearInterval(id);
  }, [fetchHealth]);

  const overallBadge = data
    ? data.status === "healthy" ? "bg-green-950 text-green-400"
    : data.status === "degraded" ? "bg-yellow-950 text-yellow-400"
    : "bg-red-950 text-red-400"
    : "";

  const metrics = data
    ? [
        { label: "Avg response time", value: `${data.metrics.avg_response_ms}ms`,          ok: data.metrics.avg_response_ms  < 200 },
        { label: "Requests today",     value: data.metrics.requests_today.toLocaleString(), ok: true },
        { label: "Active sessions",    value: String(data.metrics.active_sessions),         ok: true },
        { label: "Error rate",         value: `${data.metrics.error_rate_pct}%`,            ok: data.metrics.error_rate_pct   < 1   },
      ]
    : [];

  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <Button
          size="sm"
          variant="secondary"
          icon={<RefreshCw size={13} className={loading ? "animate-spin" : ""} />}
          onClick={fetchHealth}
          disabled={loading}
        >
          {loading ? "Checking…" : "Refresh"}
        </Button>

        {lastChecked && (
          <span className="text-xs text-gray-600">
            Last checked:{" "}
            {lastChecked.toLocaleTimeString([], {
              hour: "2-digit", minute: "2-digit", second: "2-digit",
            })}
          </span>
        )}

        {data && (
          <span className={clsx("ml-auto text-xs font-medium px-2.5 py-1 rounded-full", overallBadge)}>
            {data.status}
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !data && (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      )}

      {/* Content */}
      {data && (
        <>
          {/* Metric cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {metrics.map((m) => (
              <HealthMetricCard key={m.label} label={m.label} value={m.value} ok={m.ok} />
            ))}
          </div>

          {/* Services + Resources */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-400">Services</h3>
              {data.services.map((s) => <ServiceRow key={s.name} service={s} />)}
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-400">System resources</h3>
              {data.resources.map((r) => <ResourceRow key={r.name} resource={r} />)}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── 3. Audit Logs panel ──────────────────────────────────────────────────────

function AuditLogsPanel() {
  // Filter inputs (what the user is typing)
  const [userIdInput,   setUserIdInput]   = useState("");
  const [actionType,    setActionType]    = useState<ActionType>("");
  const [keywordInput,  setKeywordInput]  = useState("");

  // Applied filters (sent to API)
  const [appliedUserId,   setAppliedUserId]   = useState("");
  const [appliedAction,   setAppliedAction]   = useState<ActionType>("");
  const [appliedKeyword,  setAppliedKeyword]  = useState("");

  const [page,    setPage]    = useState(1);
  const [data,    setData]    = useState<AuditLogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchLogs = useCallback(async (
    uid: string,
    act: ActionType,
    kw:  string,
    pg:  number,
  ) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = { page: pg, limit: AUDIT_PER_PAGE };
      if (uid) params.user_id     = uid;
      if (act) params.action_type = act;

      const { data: json } = await api.get<AuditLogsResponse>("/admin/logs", { params });

      // Client-side keyword filter (remove if backend supports it)
      if (kw) {
        const needle = kw.toLowerCase();
        json.logs = json.logs.filter((l) => {
        const detailsText = JSON.stringify(l.details ?? {})
       .toLowerCase();
        return detailsText.includes(needle);
  });
}


      setData(json);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Failed to load audit logs.";
      setError(msg);
      toast.error("Could not load audit logs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs(appliedUserId, appliedAction, appliedKeyword, page);
  }, [appliedUserId, appliedAction, appliedKeyword, page, fetchLogs]);

  // Commit text-field filters on Enter / blur
  const commit = () => {
    setAppliedUserId(userIdInput.trim());
    setAppliedKeyword(keywordInput.trim());
    setPage(1);
  };

  const handleActionChange = (v: ActionType) => {
    setActionType(v);
    setAppliedAction(v);
    setPage(1);
  };

  const handleKeywordChange = (v: string) => {
    setKeywordInput(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setAppliedKeyword(v.trim());
      setPage(1);
    }, 500);
  };

  const clearAll = () => {
    setUserIdInput(""); setAppliedUserId("");
    setActionType("");  setAppliedAction("");
    setKeywordInput(""); setAppliedKeyword("");
    setPage(1);
  };

  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;
  const start = (page - 1) * AUDIT_PER_PAGE + 1;
  const end   = Math.min(total, page * AUDIT_PER_PAGE);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <div className="space-y-1.5">
          <label className="field-label">User ID</label>
          <input
            type="text"
            value={userIdInput}
            placeholder="e.g. usr_021"
            onChange={(e) => setUserIdInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && commit()}
            onBlur={commit}
            className="field"
          />
        </div>

        <div className="space-y-1.5">
          <label className="field-label">Action type</label>
          <select
          aria-label="Filter by action type"
            value={actionType}
            onChange={(e) => handleActionChange(e.target.value as ActionType)}
            className="field"
          >
            <option value="">All actions</option>
            {AUDIT_ACTION_TYPES.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="field-label">Search details</label>
          <input
            type="text"
            value={keywordInput}
            placeholder="keyword…"
            onChange={(e) => handleKeywordChange(e.target.value)}
            className="field"
          />
        </div>

        <Button variant="secondary" size="sm" onClick={clearAll}>
          Clear filters
        </Button>
      </div>

      {/* Result count */}
      <p className="text-xs text-gray-500">
        {loading
          ? "Loading…"
          : `Showing ${start}–${end} of ${total} entries, newest first`}
      </p>

      {/* Error */}
      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      {loading && !data ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <Card padding="p-0">
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th className="whitespace-nowrap">Timestamp</th>
                  <th>User ID</th>
                  <th>Action</th>
                  <th>Details</th>
                  <th>IP address</th>
                </tr>
              </thead>
              <tbody>
                {data?.logs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center py-10 text-gray-600 text-sm">
                      No audit logs match your filters.
                    </td>
                  </tr>
                )}
                {data?.logs.map((log) => (
                  <tr key={log.id}>
                    <td className="text-gray-500 text-xs whitespace-nowrap font-mono">
                      {new Date(log.timestamp).toISOString().replace("T", " ").slice(0, 19)}
                    </td>
                    <td className="font-mono text-xs text-gray-300">{log.user_id}</td>
                    <td><ActionBadge action={log.action_type} /></td>
                    <td className="text-gray-400 text-sm max-w-xs">
                   <pre className="whitespace-pre-wrap break-words text-xs">
                      {log.details
                       ? JSON.stringify(log.details, null, 2)
                      : "—"}
                   </pre>
                   </td>

                    <td className="text-gray-600 text-xs font-mono">{log.ip_address}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">Page {page} of {pages}</span>
        <AuditPagination page={page} pages={pages} onChange={setPage} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page root
// ─────────────────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabId>("users");

  return (
    <>
      <Head><title>Admin — ForensicEdge</title></Head>

      <AppLayout title="Admin" requiredRole="admin">
        <TabBar active={activeTab} onChange={setActiveTab} />

        {activeTab === "users"  && <UsersPanel />}
        {activeTab === "health" && <SystemHealthPanel />}
        {activeTab === "audit"  && <AuditLogsPanel />}
      </AppLayout>
    </>
  );
}