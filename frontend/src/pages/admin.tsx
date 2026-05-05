/**
 * src/pages/admin.tsx
 * ─────────────────────
 * Admin-only page with four tabs:
 *
 *   1. Users              — list / create / activate / deactivate / delete / edit
 *   2. Investigator Intel — search users → full profile + activity timeline + cases
 *   3. System health      — GET /admin/health (live service + resource status)
 *   4. Audit logs         — GET /admin/logs?user_id=&action_type=&page=&limit=
 *
 * Security note
 * ──────────────
 *   requiredRole="admin" on AppLayout redirects non-admins to /dashboard
 *   before this component renders. The server enforces the same rules.
 *
 * New in this version: User Intelligence / Investigator Activity Tracking System
 * ───────────────────────────────────────────────────────────────────────────────
 *   Phase 1  ✅ User search  ✅ User profile page  ✅ Activity timeline
 *   Phase 2  ✅ Case assignments  ✅ Evidence ownership  ✅ Login history
 *   Phase 3  Ready for AI anomaly detection / productivity analytics hook-in
 *
 *   API endpoints consumed (new):
 *     GET /admin/investigator/:userId/profile    → InvestigatorProfile
 *     GET /admin/investigator/:userId/activity   → ActivityEvent[]
 *     GET /admin/investigator/:userId/cases      → InvestigatorCase[]
 *     GET /admin/investigator/:userId/evidence   → EvidenceItem[]
 *     GET /admin/investigator/:userId/logins     → LoginEvent[]
 *     GET /admin/investigator/search?q=          → User[]
 *
 *   If your backend doesn't have these yet, the panel shows a graceful error
 *   and you can connect the real endpoints once built.
 */

import Modal from "../components/ui/modal";
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
  Pencil,
  Search,
  ChevronLeft,
  Clock,
  Folder,
  Image,
  LogIn,
  FileText,
  Shield,
  AlertTriangle,
  BarChart2,
  CheckCircle,
  XCircle,
  ArrowUpRight,
  Hash,
  Upload,
  GitCompare,
  BookOpen,
  Eye,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import { RoleBadge, ActiveBadge } from "../components/ui/Badge";
import Spinner from "../components/ui/Spinner";
import api from "../services/api";
import { User } from "../services/authService";

// ─────────────────────────────────────────────────────────────────────────────
// Shared types — existing
// ─────────────────────────────────────────────────────────────────────────────

interface UserListResponse {
  total: number;
  users: User[];
}

type ServiceStatus = "ok" | "warn" | "error";

interface HealthService {
  name: string;
  status: ServiceStatus;
  latency_ms: number | null;
  detail: string;
}

interface HealthResource {
  name: string;
  value: string;
  pct: number;
  status: ServiceStatus;
}

interface HealthData {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  metrics: {
    avg_response_ms: number;
    requests_today: number;
    active_sessions: number;
    error_rate_pct: number;
  };
  services: HealthService[];
  resources: HealthResource[];
}

interface AuditLog {
  id: number;
  user_id: number | null;
  action_type: string;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  timestamp: string;
}

interface AuditLogsResponse {
  logs: AuditLog[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// New types — Investigator Intelligence System
// ─────────────────────────────────────────────────────────────────────────────

type ActivityEventType =
  | "upload"
  | "comparison"
  | "report"
  | "login"
  | "logout"
  | "case_modified"
  | "case_created"
  | "feedback";

interface ActivityEvent {
  id: number;
  event_type: ActivityEventType;
  description: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
  case_id?: string;
  ip_address?: string;
}

interface InvestigatorCase {
  case_id: string;
  title: string;
  case_type: string;
  status: "active" | "completed" | "pending";
  role: string;
  evidence_count: number;
  reports_authored: number;
  last_activity: string;
}

interface EvidenceItem {
  id: number;
  image_id: string;
  filename: string;
  evidence_type: string;
  case_id: string;
  uploaded_at: string;
  ai_analyzed: boolean;
  report_generated: boolean;
  file_hash?: string;
}

interface LoginEvent {
  id: number;
  timestamp: string;
  ip_address: string;
  user_agent?: string;
  success: boolean;
}

interface InvestigatorProfile {
  user: User;
  stats: {
    total_uploads: number;
    total_comparisons: number;
    total_reports: number;
    total_cases: number;
    last_login: string | null;
    last_active: string | null;
    login_count_30d: number;
    avg_daily_actions: number;
  };
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

type ActionType = (typeof AUDIT_ACTION_TYPES)[number] | "";

const ACTION_BADGE_CLASSES: Record<string, string> = {
  image_uploaded: "bg-blue-950  text-blue-400",
  comparison_completed: "bg-green-950 text-green-400",
  user_login: "bg-purple-950 text-purple-400",
  report_generated: "bg-yellow-950 text-yellow-400",
  user_deleted: "bg-red-950   text-red-400",
  admin_action: "bg-pink-950  text-pink-400",
};

const AUDIT_PER_PAGE = 15;

const STATUS_DOT: Record<ServiceStatus, string> = {
  ok: "bg-green-500",
  warn: "bg-yellow-500",
  error: "bg-red-500",
};

const STATUS_BADGE: Record<ServiceStatus, string> = {
  ok: "bg-green-950  text-green-400",
  warn: "bg-yellow-950 text-yellow-400",
  error: "bg-red-950    text-red-400",
};

const ACTIVITY_CONFIG: Record<
  ActivityEventType,
  { icon: React.ReactNode; color: string; bg: string }
> = {
  upload: {
    icon: <Upload size={13} />,
    color: "text-blue-400",
    bg: "bg-blue-950",
  },
  comparison: {
    icon: <GitCompare size={13} />,
    color: "text-green-400",
    bg: "bg-green-950",
  },
  report: {
    icon: <FileText size={13} />,
    color: "text-yellow-400",
    bg: "bg-yellow-950",
  },
  login: {
    icon: <LogIn size={13} />,
    color: "text-purple-400",
    bg: "bg-purple-950",
  },
  logout: {
    icon: <LogIn size={13} className="rotate-180" />,
    color: "text-gray-400",
    bg: "bg-gray-800",
  },
  case_modified: {
    icon: <Folder size={13} />,
    color: "text-orange-400",
    bg: "bg-orange-950",
  },
  case_created: {
    icon: <Folder size={13} />,
    color: "text-cyan-400",
    bg: "bg-cyan-950",
  },
  feedback: {
    icon: <BookOpen size={13} />,
    color: "text-pink-400",
    bg: "bg-pink-950",
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Tab bar
// ─────────────────────────────────────────────────────────────────────────────

type TabId = "users" | "intel" | "health" | "audit";

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  { id: "users", label: "Users", icon: <Users size={14} /> },
  {
    id: "intel",
    label: "Investigator Intel",
    icon: <Shield size={14} />,
  },
  { id: "health", label: "System Health", icon: <Activity size={14} /> },
  { id: "audit", label: "Audit Logs", icon: <ScrollText size={14} /> },
];

function TabBar({
  active,
  onChange,
}: {
  active: TabId;
  onChange: (id: TabId) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-gray-800 mb-6 overflow-x-auto">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={clsx(
            "flex items-center gap-1.5 px-4 py-2.5 text-sm -mb-px border-b-2 transition-colors whitespace-nowrap",
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

// ─────────────────────────────────────────────────────────────────────────────
// ── Investigator Intelligence System ─────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

// ── Stat mini-card ──────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon,
  color = "text-white",
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color?: string;
}) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center shrink-0 text-gray-400">
        {icon}
      </div>
      <div>
        <p className="text-xs text-gray-500 mb-0.5">{label}</p>
        <p className={clsx("text-xl font-semibold", color)}>{value}</p>
      </div>
    </div>
  );
}

// ── Activity timeline row ────────────────────────────────────────────────────

function TimelineRow({
  event,
  isLast,
}: {
  event: ActivityEvent;
  isLast: boolean;
}) {
  const cfg = ACTIVITY_CONFIG[event.event_type] ?? {
    icon: <Clock size={13} />,
    color: "text-gray-400",
    bg: "bg-gray-800",
  };

  const time = new Date(event.timestamp);
  const timeStr = time.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const dateStr = time.toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });

  return (
    <div className="flex gap-3">
      {/* Spine */}
      <div className="flex flex-col items-center">
        <div
          className={clsx(
            "w-7 h-7 rounded-full flex items-center justify-center shrink-0",
            cfg.bg,
            cfg.color
          )}
        >
          {cfg.icon}
        </div>
        {!isLast && <div className="w-px flex-1 bg-gray-800 mt-1" />}
      </div>

      {/* Content */}
      <div className={clsx("pb-4 flex-1 min-w-0", isLast && "pb-0")}>
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-gray-200 leading-snug">
            {event.description}
          </p>
          <div className="text-right shrink-0">
            <p className="text-xs text-gray-400 font-mono">{timeStr}</p>
            <p className="text-xs text-gray-600">{dateStr}</p>
          </div>
        </div>
        {event.case_id && (
          <span className="inline-block mt-1 text-xs text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded-full">
            {event.case_id}
          </span>
        )}
        {event.ip_address && (
          <span className="ml-1.5 inline-block mt-1 text-xs text-gray-600 font-mono">
            {event.ip_address}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Case row ─────────────────────────────────────────────────────────────────

function CaseRow({ c }: { c: InvestigatorCase }) {
  const statusColors = {
    active: "bg-green-950 text-green-400",
    completed: "bg-gray-800 text-gray-400",
    pending: "bg-yellow-950 text-yellow-400",
  };

  return (
    <div className="flex items-center gap-4 bg-gray-900 rounded-xl px-4 py-3">
      <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center shrink-0">
        <Folder size={15} className="text-gray-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-white font-mono">
            {c.case_id}
          </span>
          <span
            className={clsx(
              "text-xs px-2 py-0.5 rounded-full font-medium",
              statusColors[c.status]
            )}
          >
            {c.status}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5 truncate">{c.title}</p>
        <p className="text-xs text-gray-600 mt-0.5">
          {c.case_type} · Role: {c.role}
        </p>
      </div>
      <div className="text-right shrink-0 space-y-0.5">
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Image size={11} /> {c.evidence_count}
          </span>
          <span className="flex items-center gap-1">
            <FileText size={11} /> {c.reports_authored}
          </span>
        </div>
        <p className="text-xs text-gray-600">
          {new Date(c.last_activity).toLocaleDateString([], {
            month: "short",
            day: "numeric",
          })}
        </p>
      </div>
    </div>
  );
}

// ── Evidence row ──────────────────────────────────────────────────────────────

function EvidenceRow({ item }: { item: EvidenceItem }) {
  return (
    <div className="flex items-center gap-3 bg-gray-900 rounded-xl px-4 py-3">
      <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center shrink-0">
        <Image size={14} className="text-gray-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white font-medium truncate">
          {item.filename}
        </p>
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          <span className="text-xs text-gray-500 font-mono">{item.case_id}</span>
          <span className="text-xs text-gray-600">{item.evidence_type}</span>
          {item.file_hash && (
            <span className="text-xs text-gray-700 font-mono flex items-center gap-0.5">
              <Hash size={9} />
              {item.file_hash.slice(0, 12)}…
            </span>
          )}
        </div>
      </div>
      <div className="text-right shrink-0 space-y-1">
        <div className="flex items-center gap-1.5 justify-end">
          {item.ai_analyzed ? (
            <CheckCircle size={13} className="text-green-400" />
          ) : (
            <XCircle size={13} className="text-gray-600" />
          )}
          <span className="text-xs text-gray-500">AI</span>
        </div>
        <div className="flex items-center gap-1.5 justify-end">
          {item.report_generated ? (
            <CheckCircle size={13} className="text-green-400" />
          ) : (
            <XCircle size={13} className="text-gray-600" />
          )}
          <span className="text-xs text-gray-500">Report</span>
        </div>
        <p className="text-xs text-gray-600">
          {new Date(item.uploaded_at).toLocaleDateString([], {
            month: "short",
            day: "numeric",
          })}
        </p>
      </div>
    </div>
  );
}

// ── Login history row ────────────────────────────────────────────────────────

function LoginRow({ event }: { event: LoginEvent }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-800 last:border-0">
      {event.success ? (
        <CheckCircle size={14} className="text-green-400 shrink-0" />
      ) : (
        <XCircle size={14} className="text-red-400 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-300 font-mono">{event.ip_address}</p>
        {event.user_agent && (
          <p className="text-xs text-gray-600 truncate mt-0.5">
            {event.user_agent}
          </p>
        )}
      </div>
      <p className="text-xs text-gray-500 whitespace-nowrap font-mono shrink-0">
        {new Date(event.timestamp)
          .toISOString()
          .replace("T", " ")
          .slice(0, 16)}
      </p>
    </div>
  );
}

// ── Investigator full profile view ───────────────────────────────────────────

type ProfileTab = "timeline" | "cases" | "evidence" | "logins";

function InvestigatorProfileView({
  userId,
  onBack,
}: {
  userId: number;
  onBack: () => void;
}) {
  const [profile, setProfile] = useState<InvestigatorProfile | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [cases, setCases] = useState<InvestigatorCase[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [logins, setLogins] = useState<LoginEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ProfileTab>("timeline");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch profile + stats
        const { data: profileData } = await api.get<InvestigatorProfile>(
          `/admin/investigator/${userId}/profile`
        );
        setProfile(profileData);

        // Fetch all sub-resources in parallel
        const [actRes, caseRes, evRes, loginRes] = await Promise.allSettled([
          api.get<ActivityEvent[]>(
            `/admin/investigator/${userId}/activity?limit=50`
          ),
          api.get<InvestigatorCase[]>(
            `/admin/investigator/${userId}/cases`
          ),
          api.get<EvidenceItem[]>(
            `/admin/investigator/${userId}/evidence`
          ),
          api.get<LoginEvent[]>(
            `/admin/investigator/${userId}/logins?limit=20`
          ),
        ]);

        if (actRes.status === "fulfilled") setActivity(actRes.value.data);
        if (caseRes.status === "fulfilled") setCases(caseRes.value.data);
        if (evRes.status === "fulfilled") setEvidence(evRes.value.data);
        if (loginRes.status === "fulfilled") setLogins(loginRes.value.data);
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response
            ?.data?.detail ?? "Could not load investigator profile.";
        setError(detail);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [userId]);

  const profileTabs: { id: ProfileTab; label: string; icon: React.ReactNode }[] =
    [
      { id: "timeline", label: "Activity Timeline", icon: <Clock size={13} /> },
      { id: "cases", label: `Cases (${cases.length})`, icon: <Folder size={13} /> },
      {
        id: "evidence",
        label: `Evidence (${evidence.length})`,
        icon: <Image size={13} />,
      },
      { id: "logins", label: "Login History", icon: <LogIn size={13} /> },
    ];

  if (loading)
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <Spinner size="lg" />
        <p className="text-gray-600 text-sm">Loading investigator profile…</p>
      </div>
    );

  if (error)
    return (
      <div className="space-y-4">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-white transition-colors"
        >
          <ChevronLeft size={15} /> Back to search
        </button>
        <div className="bg-red-950 border border-red-800 rounded-xl px-5 py-4 text-red-400 text-sm">
          <p className="font-medium mb-1">Failed to load profile</p>
          <p className="text-red-500 text-xs">{error}</p>
          <p className="text-red-600 text-xs mt-2">
            Make sure the{" "}
            <code className="text-red-400">/admin/investigator/:id/*</code>{" "}
            endpoints are implemented on the backend.
          </p>
        </div>
      </div>
    );

  if (!profile) return null;

  const { user, stats } = profile;

  const relativeTime = (iso: string | null) => {
    if (!iso) return "Never";
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins} minute${mins !== 1 ? "s" : ""} ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs} hour${hrs !== 1 ? "s" : ""} ago`;
    const days = Math.floor(hrs / 24);
    return `${days} day${days !== 1 ? "s" : ""} ago`;
  };

  const activeCases = cases.filter((c) => c.status === "active").length;
  const completedCases = cases.filter((c) => c.status === "completed").length;

  return (
    <div className="space-y-6">
      {/* Back */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-white transition-colors"
      >
        <ChevronLeft size={15} /> Back to search
      </button>

      {/* Profile header card */}
      <Card>
        <div className="flex items-start gap-4 flex-wrap">
          {/* Avatar */}
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center text-white text-xl font-semibold shrink-0 border border-gray-700">
            {user.full_name.charAt(0).toUpperCase()}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-white font-semibold text-lg">
                {user.full_name}
              </h2>
              <RoleBadge role={user.role} />
              <ActiveBadge isActive={user.is_active} />
            </div>
            <p className="text-gray-400 text-sm mt-0.5">{user.email}</p>
            <div className="flex items-center gap-4 mt-2 flex-wrap text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <Clock size={11} />
                Joined{" "}
                {new Date(user.created_at).toLocaleDateString([], {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              <span className="flex items-center gap-1">
                <LogIn size={11} />
                Last login: {relativeTime(stats.last_login)}
              </span>
              <span className="flex items-center gap-1">
                <Activity size={11} />
                Last active: {relativeTime(stats.last_active)}
              </span>
            </div>
          </div>

          {/* Quick risk indicator */}
          <div className="shrink-0">
            {stats.avg_daily_actions > 50 ? (
              <div className="flex items-center gap-1.5 bg-yellow-950 text-yellow-400 text-xs px-3 py-1.5 rounded-full border border-yellow-900">
                <AlertTriangle size={12} />
                High activity
              </div>
            ) : (
              <div className="flex items-center gap-1.5 bg-green-950 text-green-400 text-xs px-3 py-1.5 rounded-full border border-green-900">
                <CheckCircle size={12} />
                Normal activity
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Stat grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Total uploads"
          value={stats.total_uploads}
          icon={<Upload size={15} />}
          color="text-blue-400"
        />
        <StatCard
          label="Comparisons run"
          value={stats.total_comparisons}
          icon={<GitCompare size={15} />}
          color="text-green-400"
        />
        <StatCard
          label="Reports authored"
          value={stats.total_reports}
          icon={<FileText size={15} />}
          color="text-yellow-400"
        />
        <StatCard
          label="Cases worked"
          value={stats.total_cases}
          icon={<Folder size={15} />}
          color="text-cyan-400"
        />
      </div>

      {/* Case summary row */}
      {cases.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-900 rounded-xl p-4 text-center">
            <p className="text-2xl font-semibold text-green-400">{activeCases}</p>
            <p className="text-xs text-gray-500 mt-1">Active cases</p>
          </div>
          <div className="bg-gray-900 rounded-xl p-4 text-center">
            <p className="text-2xl font-semibold text-gray-400">{completedCases}</p>
            <p className="text-xs text-gray-500 mt-1">Completed cases</p>
          </div>
          <div className="bg-gray-900 rounded-xl p-4 text-center">
            <p className="text-2xl font-semibold text-purple-400">
              {stats.login_count_30d}
            </p>
            <p className="text-xs text-gray-500 mt-1">Logins (30d)</p>
          </div>
        </div>
      )}

      {/* Sub-tabs */}
      <div className="flex gap-1 border-b border-gray-800 overflow-x-auto">
        {profileTabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-2 text-xs -mb-px border-b-2 transition-colors whitespace-nowrap",
              activeTab === t.id
                ? "border-white text-white font-medium"
                : "border-transparent text-gray-500 hover:text-gray-300"
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Timeline tab */}
      {activeTab === "timeline" && (
        <div>
          {activity.length === 0 ? (
            <div className="text-center py-12 text-gray-600 text-sm">
              No activity recorded yet.
            </div>
          ) : (
            <div className="space-y-0">
              {activity.map((event, i) => (
                <TimelineRow
                  key={event.id}
                  event={event}
                  isLast={i === activity.length - 1}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cases tab */}
      {activeTab === "cases" && (
        <div className="space-y-2">
          {cases.length === 0 ? (
            <div className="text-center py-12 text-gray-600 text-sm">
              No cases assigned.
            </div>
          ) : (
            cases.map((c) => <CaseRow key={c.case_id} c={c} />)
          )}
        </div>
      )}

      {/* Evidence tab */}
      {activeTab === "evidence" && (
        <div className="space-y-2">
          {evidence.length === 0 ? (
            <div className="text-center py-12 text-gray-600 text-sm">
              No evidence uploaded.
            </div>
          ) : (
            evidence.map((item) => <EvidenceRow key={item.id} item={item} />)
          )}
        </div>
      )}

      {/* Logins tab */}
      {activeTab === "logins" && (
        <Card>
          {logins.length === 0 ? (
            <div className="text-center py-10 text-gray-600 text-sm">
              No login records found.
            </div>
          ) : (
            <div>
              {logins.map((l) => (
                <LoginRow key={l.id} event={l} />
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

// ── Investigator search + panel root ─────────────────────────────────────────

function InvestigatorIntelPanel() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<User[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }
    setSearching(true);
    setHasSearched(true);
    try {
      const { data } = await api.get<{ users: User[] }>(
        "/admin/investigator/search",
        { params: { q: q.trim(), limit: 20 } }
      );
      setResults(data.users ?? []);
    } catch {
      // Fallback: search local users list from /admin/users
      try {
        const { data } = await api.get<UserListResponse>("/admin/users", {
          params: { limit: 100 },
        });
        const needle = q.toLowerCase();
        setResults(
          data.users.filter(
            (u) =>
              u.full_name.toLowerCase().includes(needle) ||
              u.email.toLowerCase().includes(needle) ||
              String(u.id).includes(needle)
          )
        );
      } catch {
        toast.error("Search failed.");
        setResults([]);
      }
    } finally {
      setSearching(false);
    }
  }, []);

  const handleQueryChange = (v: string) => {
    setQuery(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(v), 400);
  };

  if (selectedUserId !== null) {
    return (
      <InvestigatorProfileView
        userId={selectedUserId}
        onBack={() => {
          setSelectedUserId(null);
        }}
      />
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h2 className="text-white font-semibold text-lg flex items-center gap-2">
          <Shield size={18} className="text-gray-400" />
          Investigator Intelligence
        </h2>
        <p className="text-gray-500 text-sm mt-0.5">
          Search by name, email, or user ID to open a complete investigator
          profile with activity timeline, case assignments, and evidence
          ownership.
        </p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <div className="absolute inset-y-0 left-3.5 flex items-center pointer-events-none text-gray-500">
          {searching ? <Spinner size="sm" /> : <Search size={15} />}
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          placeholder="Search by name, email, or user ID…"
          className="field pl-9 text-sm"
          autoFocus
        />
      </div>

      {/* Phase badges */}
      <div className="flex gap-2 flex-wrap">
        {[
          { label: "User Search", phase: 1 },
          { label: "Profile Page", phase: 1 },
          { label: "Activity Timeline", phase: 1 },
          { label: "Case Assignments", phase: 2 },
          { label: "Evidence Ownership", phase: 2 },
          { label: "Login History", phase: 2 },
        ].map((f) => (
          <span
            key={f.label}
            className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-gray-800 text-gray-400"
          >
            <CheckCircle size={10} className="text-green-500" />
            {f.label}
          </span>
        ))}
        {[
          { label: "AI Anomaly Detection", phase: 3 },
          { label: "Productivity Analytics", phase: 3 },
        ].map((f) => (
          <span
            key={f.label}
            className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-gray-900 text-gray-600 border border-gray-800"
          >
            <ArrowUpRight size={10} />
            {f.label} (Phase 3)
          </span>
        ))}
      </div>

      {/* Results */}
      {hasSearched && results.length === 0 && !searching && (
        <div className="text-center py-12 text-gray-600 text-sm">
          No investigators found matching "{query}".
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">
            {results.length} result{results.length !== 1 ? "s" : ""}
          </p>
          {results.map((user) => (
            <button
              key={user.id}
              onClick={() => setSelectedUserId(user.id)}
              className="w-full text-left bg-gray-900 hover:bg-gray-800 border border-transparent hover:border-gray-700 rounded-xl px-4 py-3 transition-all group"
            >
              <div className="flex items-center gap-3">
                {/* Avatar */}
                <div className="w-9 h-9 rounded-xl bg-gray-800 flex items-center justify-center text-white text-sm font-semibold shrink-0 border border-gray-700 group-hover:border-gray-600 transition-colors">
                  {user.full_name.charAt(0).toUpperCase()}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white text-sm font-medium">
                      {user.full_name}
                    </span>
                    <RoleBadge role={user.role} />
                    <ActiveBadge isActive={user.is_active} />
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 flex-wrap">
                    <span className="text-gray-500 text-xs">{user.email}</span>
                    <span className="text-gray-700 text-xs font-mono">
                      ID:{user.id}
                    </span>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex items-center gap-1.5 text-gray-600 group-hover:text-white transition-colors text-xs shrink-0">
                  <Eye size={13} />
                  <span>View profile</span>
                  <ArrowUpRight size={13} />
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Empty state — no search yet */}
      {!hasSearched && (
        <Card className="py-12">
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center">
              <Shield size={24} className="text-gray-600" />
            </div>
            <div>
              <p className="text-gray-400 text-sm font-medium">
                Search for an investigator
              </p>
              <p className="text-gray-600 text-xs mt-1">
                Enter a name, email address, or numeric user ID above to open
                their full accountability profile.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2 w-full max-w-lg">
              {[
                {
                  icon: <BarChart2 size={14} />,
                  label: "Activity auditing",
                  desc: "Complete forensic trail of every action",
                },
                {
                  icon: <Folder size={14} />,
                  label: "Case tracking",
                  desc: "Cases worked, role, and contributions",
                },
                {
                  icon: <Shield size={14} />,
                  label: "Insider protection",
                  desc: "Detect misuse and anomalous behaviour",
                },
              ].map((f) => (
                <div
                  key={f.label}
                  className="bg-gray-900 rounded-xl p-3 text-left"
                >
                  <div className="text-gray-500 mb-1.5">{f.icon}</div>
                  <p className="text-gray-300 text-xs font-medium">{f.label}</p>
                  <p className="text-gray-600 text-xs mt-0.5">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Health helpers (unchanged) ────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

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
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1.5">
        {label}
      </p>
      <p
        className={clsx(
          "text-2xl font-semibold",
          ok ? "text-green-400" : "text-yellow-400"
        )}
      >
        {value}
      </p>
    </div>
  );
}

function ServiceRow({ service }: { service: HealthService }) {
  return (
    <div className="flex items-center gap-3 bg-gray-900 rounded-xl px-4 py-3">
      <span
        className={clsx(
          "w-2 h-2 rounded-full shrink-0",
          STATUS_DOT[service.status]
        )}
      />
      <span className="text-sm font-medium text-white flex-1">
        {service.name}
      </span>
      <span className="text-xs text-gray-500">
        {service.latency_ms != null ? `${service.latency_ms}ms` : "—"}
      </span>
      <span
        className={clsx(
          "text-xs px-2.5 py-0.5 rounded-full font-medium",
          STATUS_BADGE[service.status]
        )}
      >
        {service.status === "ok"
          ? "Healthy"
          : service.status === "warn"
          ? "Warning"
          : "Error"}
      </span>
    </div>
  );
}

function ResourceRow({ resource }: { resource: HealthResource }) {
  const pct = Math.min(100, Math.max(0, resource.pct));
  const barColor =
    resource.status === "ok"
      ? "bg-green-500"
      : resource.status === "warn"
      ? "bg-yellow-500"
      : "bg-red-500";
  return (
    <div className="flex flex-col gap-1.5 bg-gray-900 rounded-xl px-4 py-3">
      <div className="flex items-center gap-2">
        <span
          className={clsx(
            "w-2 h-2 rounded-full shrink-0",
            STATUS_DOT[resource.status]
          )}
        />
        <span className="text-sm font-medium text-white flex-1">
          {resource.name}
        </span>
        <span className="text-sm font-medium text-white">{resource.value}</span>
      </div>
      <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-500",
            barColor
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Audit helpers (unchanged) ─────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

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
    <button
      key="prev"
      onClick={() => onChange(page - 1)}
      disabled={page === 1}
      className={btnCls(false, page === 1)}
    >
      ← Prev
    </button>
  );

  if (lo > 1) {
    items.push(
      <button key="p1" onClick={() => onChange(1)} className={btnCls(false)}>
        1
      </button>
    );
    if (lo > 2)
      items.push(
        <span key="e1" className="text-gray-600 px-1">
          …
        </span>
      );
  }

  for (let i = lo; i <= hi; i++) {
    items.push(
      <button key={i} onClick={() => onChange(i)} className={btnCls(i === page)}>
        {i}
      </button>
    );
  }

  if (hi < pages) {
    if (hi < pages - 1)
      items.push(
        <span key="e2" className="text-gray-600 px-1">
          …
        </span>
      );
    items.push(
      <button
        key="last"
        onClick={() => onChange(pages)}
        className={btnCls(false)}
      >
        {pages}
      </button>
    );
  }

  items.push(
    <button
      key="next"
      onClick={() => onChange(page + 1)}
      disabled={page === pages}
      className={btnCls(false, page === pages)}
    >
      Next →
    </button>
  );

  return <div className="flex items-center gap-1">{items}</div>;
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Users panel (unchanged from original) ────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

function UsersPanel() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editFullName, setEditFullName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editRole, setEditRole] = useState<User["role"]>("analyst");
  const [editPassword, setEditPassword] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<User["role"]>("analyst");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const openEditModal = (user: User) => {
    setSelectedUser(user);
    setEditFullName(user.full_name);
    setEditEmail(user.email);
    setEditRole(user.role);
    setEditPassword("");
    setShowEditModal(true);
  };

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<UserListResponse>("/admin/users", {
        params: {
          limit: 100,
          ...(roleFilter && { role: roleFilter }),
          ...(statusFilter !== "" && {
            is_active: statusFilter === "active",
          }),
        },
      });
      setUsers(data.users);
      setTotal(data.total);
    } catch {
      toast.error("Could not load users.");
    } finally {
      setLoading(false);
    }
  }, [roleFilter, statusFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleToggleActive = async (user: User) => {
    setTogglingId(user.id);
    try {
      await api.patch(`/admin/users/${user.id}`, {
        is_active: !user.is_active,
      });
      toast.success(
        `${user.full_name} ${user.is_active ? "deactivated" : "activated"}.`
      );
      await loadUsers();
    } catch {
      toast.error("Update failed.");
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async (user: User) => {
    if (
      !confirm(
        `Permanently delete "${user.full_name}"?\n\n` +
          `This will remove their account and all associated data. ` +
          `This action cannot be undone.`
      )
    )
      return;
    setDeletingId(user.id);
    try {
      await api.delete(`/admin/users/${user.id}`);
      toast.success("User deleted.");
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
      setTotal((t) => t - 1);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Delete failed.";
      toast.error(detail);
    } finally {
      setDeletingId(null);
    }
  };

  const handleUpdateUser = async () => {
    if (!selectedUser) return;
    setSavingEdit(true);
    try {
      const payload: Record<string, unknown> = {
        full_name: editFullName.trim(),
        email: editEmail.trim(),
        role: editRole,
      };
      if (editPassword.trim()) {
        payload.password = editPassword.trim();
      }
      await api.patch(`/admin/users/${selectedUser.id}`, payload);
      toast.success("User updated successfully.");
      setShowEditModal(false);
      await loadUsers();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Update failed.";
      toast.error(detail);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setFormError("");
    setCreating(true);
    try {
      await api.post("/admin/users", {
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role,
      });
      toast.success(`User "${fullName}" created.`);
      setFullName("");
      setEmail("");
      setPassword("");
      setRole("analyst");
      setShowForm(false);
      await loadUsers();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Creation failed.";
      setFormError(detail);
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-white font-semibold text-lg">Users</h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {loading
                ? "Loading…"
                : `${total} registered user${total !== 1 ? "s" : ""}`}
            </p>
          </div>
          <Button
            size="sm"
            icon={showForm ? <ChevronUp size={14} /> : <Plus size={14} />}
            onClick={() => {
              setShowForm((v) => !v);
              setFormError("");
            }}
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
                  <label htmlFor="role" className="field-label">
                    Role
                  </label>
                  <select
                    id="role"
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
                  onClick={() => {
                    setShowForm(false);
                    setFormError("");
                  }}
                  disabled={creating}
                >
                  Cancel
                </Button>
              </div>
              <p className="text-gray-600 text-xs">
                The user will log in with this temporary password and should
                change it immediately via{" "}
                <strong className="text-gray-500">
                  Settings → Password
                </strong>
                .
              </p>
            </form>
          </Card>
        )}

        {/* Filters */}
        <Card>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <label className="field-label">Role</label>
              <select
                aria-label="Filter by role"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="field"
              >
                <option value="">All roles</option>
                <option value="admin">Admin</option>
                <option value="analyst">Analyst</option>
                <option value="ai_engineer">AI Engineer</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="field-label">Status</label>
              <select
                aria-label="Filter by account status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="field"
              >
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div className="flex items-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setRoleFilter("");
                  setStatusFilter("");
                }}
              >
                Clear filters
              </Button>
            </div>
          </div>
        </Card>

        {/* Table */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
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
                    <th className="w-28">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td>
                        <span className="text-white font-medium">
                          {user.full_name}
                        </span>
                      </td>
                      <td className="text-gray-400 text-sm">{user.email}</td>
                      <td>
                        <RoleBadge role={user.role} />
                      </td>
                      <td>
                        <ActiveBadge isActive={user.is_active} />
                      </td>
                      <td className="text-gray-500 text-xs whitespace-nowrap">
                        {new Date(user.created_at).toLocaleDateString(
                          undefined,
                          {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          }
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleToggleActive(user)}
                            disabled={togglingId === user.id}
                            title={
                              user.is_active
                                ? "Deactivate account"
                                : "Activate account"
                            }
                            className={clsx(
                              "p-1.5 rounded-lg transition-colors text-gray-500 hover:bg-gray-800",
                              user.is_active
                                ? "hover:text-yellow-400"
                                : "hover:text-green-400"
                            )}
                          >
                            {togglingId === user.id ? (
                              <Spinner size="sm" />
                            ) : user.is_active ? (
                              <UserX size={15} />
                            ) : (
                              <UserCheck size={15} />
                            )}
                          </button>
                          <button
                            onClick={() => openEditModal(user)}
                            title="Edit user"
                            className="p-1.5 rounded-lg text-gray-500 hover:text-blue-400 hover:bg-gray-800 transition-colors"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            onClick={() => handleDelete(user)}
                            disabled={deletingId === user.id}
                            title="Delete user permanently"
                            className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-gray-800 transition-colors"
                          >
                            {deletingId === user.id ? (
                              <Spinner size="sm" />
                            ) : (
                              <Trash2 size={15} />
                            )}
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

      {/* Edit modal */}
      <Modal
        open={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Edit User"
        maxWidth="max-w-lg"
      >
        <div className="space-y-4">
          <Input
            label="Full name"
            value={editFullName}
            onChange={(e) => setEditFullName(e.target.value)}
          />
          <Input
            label="Email"
            type="email"
            value={editEmail}
            onChange={(e) => setEditEmail(e.target.value)}
          />
          <div className="space-y-1.5">
            <label className="field-label">Role</label>
            <select
              aria-label="Edit user role"
              value={editRole}
              onChange={(e) => setEditRole(e.target.value as User["role"])}
              className="field"
            >
              <option value="analyst">Analyst</option>
              <option value="admin">Admin</option>
              <option value="ai_engineer">AI Engineer</option>
            </select>
          </div>
          <Input
            label="Reset password (optional)"
            type="password"
            value={editPassword}
            onChange={(e) => setEditPassword(e.target.value)}
            placeholder="Leave blank to keep current password"
          />
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => setShowEditModal(false)}
            >
              Cancel
            </Button>
            <Button loading={savingEdit} onClick={handleUpdateUser}>
              Save changes
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── System Health panel (unchanged) ──────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

function SystemHealthPanel() {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: json } = await api.get<HealthData>("/admin/health");
      setData(json);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Could not reach health endpoint.";
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
    ? data.status === "healthy"
      ? "bg-green-950 text-green-400"
      : data.status === "degraded"
      ? "bg-yellow-950 text-yellow-400"
      : "bg-red-950 text-red-400"
    : "";

  const metrics = data
    ? [
        {
          label: "Avg response time",
          value: `${data.metrics.avg_response_ms}ms`,
          ok: data.metrics.avg_response_ms < 200,
        },
        {
          label: "Requests today",
          value: data.metrics.requests_today.toLocaleString(),
          ok: true,
        },
        {
          label: "Active sessions",
          value: String(data.metrics.active_sessions),
          ok: true,
        },
        {
          label: "Error rate",
          value: `${data.metrics.error_rate_pct}%`,
          ok: data.metrics.error_rate_pct < 1,
        },
      ]
    : [];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 flex-wrap">
        <Button
          size="sm"
          variant="secondary"
          icon={
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          }
          onClick={fetchHealth}
          disabled={loading}
        >
          {loading ? "Checking…" : "Refresh"}
        </Button>
        {lastChecked && (
          <span className="text-xs text-gray-600">
            Last checked:{" "}
            {lastChecked.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
        )}
        {data && (
          <span
            className={clsx(
              "ml-auto text-xs font-medium px-2.5 py-1 rounded-full",
              overallBadge
            )}
          >
            {data.status}
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && !data && (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {metrics.map((m) => (
              <HealthMetricCard
                key={m.label}
                label={m.label}
                value={m.value}
                ok={m.ok}
              />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-400">Services</h3>
              {data.services.map((s) => (
                <ServiceRow key={s.name} service={s} />
              ))}
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-400">
                System resources
              </h3>
              {data.resources.map((r) => (
                <ResourceRow key={r.name} resource={r} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Audit Logs panel (unchanged) ──────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

function AuditLogsPanel() {
  const [userIdInput, setUserIdInput] = useState("");
  const [actionType, setActionType] = useState<ActionType>("");
  const [keywordInput, setKeywordInput] = useState("");
  const [appliedUserId, setAppliedUserId] = useState("");
  const [appliedAction, setAppliedAction] = useState<ActionType>("");
  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AuditLogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchLogs = useCallback(
    async (uid: string, act: ActionType, kw: string, pg: number) => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, string | number> = {
          page: pg,
          limit: AUDIT_PER_PAGE,
        };
        if (uid) params.user_id = uid;
        if (act) params.action_type = act;

        const { data: json } = await api.get<AuditLogsResponse>(
          "/admin/logs",
          { params }
        );

        if (kw) {
          const needle = kw.toLowerCase();
          json.logs = json.logs.filter((l) => {
            const detailsText = JSON.stringify(l.details ?? {}).toLowerCase();
            return detailsText.includes(needle);
          });
        }

        setData(json);
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response
            ?.data?.detail ?? "Failed to load audit logs.";
        setError(msg);
        toast.error("Could not load audit logs.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchLogs(appliedUserId, appliedAction, appliedKeyword, page);
  }, [appliedUserId, appliedAction, appliedKeyword, page, fetchLogs]);

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
    setUserIdInput("");
    setAppliedUserId("");
    setActionType("");
    setAppliedAction("");
    setKeywordInput("");
    setAppliedKeyword("");
    setPage(1);
  };

  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;
  const start = (page - 1) * AUDIT_PER_PAGE + 1;
  const end = Math.min(total, page * AUDIT_PER_PAGE);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <div className="space-y-1.5">
          <label className="field-label">User ID</label>
          <input
            type="text"
            value={userIdInput}
            placeholder="e.g. 21"
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
              <option key={a} value={a}>
                {a}
              </option>
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

      <p className="text-xs text-gray-500">
        {loading
          ? "Loading…"
          : `Showing ${start}–${end} of ${total} entries, newest first`}
      </p>

      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
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
                    <td
                      colSpan={5}
                      className="text-center py-10 text-gray-600 text-sm"
                    >
                      No audit logs match your filters.
                    </td>
                  </tr>
                )}
                {data?.logs.map((log) => (
                  <tr key={log.id}>
                    <td className="text-gray-500 text-xs whitespace-nowrap font-mono">
                      {new Date(log.timestamp)
                        .toISOString()
                        .replace("T", " ")
                        .slice(0, 19)}
                    </td>
                    <td className="font-mono text-xs text-gray-300">
                      {log.user_id}
                    </td>
                    <td>
                      <ActionBadge action={log.action_type} />
                    </td>
                    <td className="text-gray-400 text-sm max-w-xs">
                      <pre className="whitespace-pre-wrap break-words text-xs">
                        {log.details
                          ? JSON.stringify(log.details, null, 2)
                          : "—"}
                      </pre>
                    </td>
                    <td className="text-gray-600 text-xs font-mono">
                      {log.ip_address}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          Page {page} of {pages}
        </span>
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
      <Head>
        <title>Admin — ForensicEdge</title>
      </Head>

      <AppLayout title="Admin" requiredRole="admin">
        <TabBar active={activeTab} onChange={setActiveTab} />

        {activeTab === "users" && <UsersPanel />}
        {activeTab === "intel" && <InvestigatorIntelPanel />}
        {activeTab === "health" && <SystemHealthPanel />}
        {activeTab === "audit" && <AuditLogsPanel />}
      </AppLayout>
    </>
  );
}