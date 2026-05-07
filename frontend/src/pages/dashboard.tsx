/**
 * src/pages/dashboard.tsx
 * ─────────────────────────
 * Role-aware dashboard entry point.
 *
 * Routing logic
 * ──────────────
 *   admin       → <AdminDashboard>        (full system overview — everything)
 *   ai_engineer → <AiEngineerDashboard>   (ML-ops: datasets, training, metrics)
 *   analyst     → <InvestigatorDashboard> (case work: uploads, comparisons, reports)
 *
 * Admin sees the InvestigatorDashboard metrics embedded inside AdminDashboard
 * so nothing is hidden from them.
 *
 * Fixes applied vs the broken version
 * ─────────────────────────────────────
 *   1. <ProfileManagementCard /> was called as a dead statement outside JSX —
 *      moved it inside the return, rendered for every role above the welcome heading.
 *   2. <ActiveBadge active={…}> → <ActiveBadge isActive={…}> (correct prop name).
 *   3. Button variant="ghost" removed (not in the component's type union) —
 *      replaced with variant="secondary".
 *   4. Unused imports cleaned up (AlertCircle, Box).
 */

import { useEffect, useState, ReactNode, FormEvent } from "react";
import Head   from "next/head";
import Link   from "next/link";
import { useRouter } from "next/router";
import {
  Upload, GitCompare, FileText, Clock, ArrowRight,
  Database, Cpu, Layers, Play, FlaskConical,
  CheckCircle, XCircle, RefreshCw,
  TrendingUp, Zap, ChevronRight,
  Server, Users, Shield, Settings,
  UserCircle2, KeyRound, Mail,
} from "lucide-react";

import AppLayout          from "../components/layout/AppLayout";
import Card, { StatCard } from "../components/ui/Card";
import {
  EvidenceBadge,
  MatchBadge,
  RoleBadge,
  ActiveBadge,
} from "../components/ui/Badge";
import Spinner  from "../components/ui/Spinner";
import Button   from "../components/ui/Button";
import { useAuth }             from "../hooks/useAuth";
import { imageService }        from "../services/imageService";
import { compareService, SimilarityResponse } from "../services/compareService";
import { reportService }       from "../services/reportService";
import api                     from "../services/api";

// ─────────────────────────────────────────────────────────────────────────────
// ML dashboard types (kept inline; mirrors mlService.ts)
// ─────────────────────────────────────────────────────────────────────────────

export interface MlDataset {
  id:            number;
  name:          string;
  evidence_type: string;
  image_count:   number;
  size_mb:       number;
  created_at:    string;
  status:        "ready" | "processing" | "error";
}

export interface MlModelVersion {
  id:              number;
  version:         string;
  evidence_type:   string;
  accuracy:        number;
  val_loss:        number;
  created_at:      string;
  is_active:       boolean;
  training_job_id: number | null;
}

export interface MlTrainingJob {
  id:            number;
  name:          string;
  evidence_type: string;
  status:        "queued" | "running" | "completed" | "failed";
  progress_pct:  number;
  epochs_total:  number;
  epochs_done:   number;
  accuracy:      number | null;
  val_loss:      number | null;
  started_at:    string | null;
  finished_at:   string | null;
  dataset_name:  string;
}

interface MlDashboardStats {
  total_datasets:   number;
  total_models:     number;
  total_jobs:       number;
  best_accuracy:    number;
  active_job:       MlTrainingJob | null;
  recent_jobs:      MlTrainingJob[];
  latest_versions:  MlModelVersion[];
  recent_datasets:  MlDataset[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ─────────────────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, decimals = 1) {
  if (n == null) return "—";
  return n.toFixed(decimals);
}

function relTime(iso: string | null) {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared UI atoms
// ─────────────────────────────────────────────────────────────────────────────

const JOB_STATUS_CFG = {
  queued:    { icon: <Clock    size={11} />,                                    cls: "bg-gray-800   text-gray-400"  },
  running:   { icon: <RefreshCw size={11} className="animate-spin" />,          cls: "bg-blue-950   text-blue-400"  },
  completed: { icon: <CheckCircle size={11} />,                                 cls: "bg-green-950  text-green-400" },
  failed:    { icon: <XCircle  size={11} />,                                    cls: "bg-red-950    text-red-400"   },
} as const;

function JobStatusBadge({ status }: { status: MlTrainingJob["status"] }) {
  const cfg = JOB_STATUS_CFG[status];
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${cfg.cls}`}>
      {cfg.icon}{status}
    </span>
  );
}

function DatasetStatusBadge({ status }: { status: MlDataset["status"] }) {
  const map = {
    ready:      "bg-green-950  text-green-400",
    processing: "bg-yellow-950 text-yellow-400",
    error:      "bg-red-950    text-red-400",
  };
  return (
    <span className={`inline-flex items-center text-xs px-2 py-0.5 rounded-full font-medium ${map[status]}`}>
      {status}
    </span>
  );
}

function ProgressBar({ pct, color = "bg-blue-500" }: { pct: number; color?: string }) {
  return (
    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  );
}

function AccuracyRing({ value, size = 64 }: { value: number; size?: number }) {
  const r    = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const pct  = Math.min(100, Math.max(0, value));
  const dash = (pct / 100) * circ;
  const color = pct >= 90 ? "#4ade80" : pct >= 75 ? "#facc15" : "#f87171";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1f2937" strokeWidth={6} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          style={{ transition: "stroke-dasharray 1s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-bold text-white">{fmt(pct, 0)}%</span>
      </div>
    </div>
  );
}

function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
        {title}
      </h3>
      {action}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── PROFILE MANAGEMENT CARD
// ─────────────────────────────────────────────────────────────────────────────
/**
 * Shows the logged-in user's avatar, name, role, email and quick links
 * to Edit Profile and Change Password.
 *
 * Bugs fixed vs the broken version in the document:
 *   • <ActiveBadge active={…}> → <ActiveBadge isActive={…}>
 *   • Button variant="ghost"   → variant="secondary" (ghost not in union)
 */
function ProfileManagementCard() {
  const { user } = useAuth();
  const router   = useRouter();

  if (!user) return null;

  return (
    <Card padding="p-5">
      <div className="flex flex-col lg:flex-row lg:items-center gap-5">

        {/* Left — avatar + info */}
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <div className="w-16 h-16 rounded-2xl bg-blue-950 flex items-center justify-center shrink-0">
            <UserCircle2 size={34} className="text-blue-400" />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg font-semibold text-white truncate">
                {user.full_name}
              </h3>
              <RoleBadge role={user.role} />
              {/* ✅ fix: isActive, not active */}
              <ActiveBadge isActive={user.is_active} />
            </div>

            <div className="flex items-center gap-2 text-sm text-gray-400 mt-1">
              <Mail size={14} className="shrink-0" />
              <span className="truncate">{user.email}</span>
            </div>

            <p className="text-xs text-gray-600 mt-1.5">
              Manage your profile information and account security settings.
            </p>
          </div>
        </div>

        {/* Right — quick actions */}
        <div className="flex flex-wrap gap-2 shrink-0">
          <Button
            size="sm"
            icon={<UserCircle2 size={14} />}
            onClick={() => router.push("/profile")}
          >
            Edit Profile
          </Button>

          <Button
            size="sm"
            variant="secondary"
            icon={<KeyRound size={14} />}
            onClick={() => router.push("/change-password")}
          >
            Change Password
          </Button>

          {/* ✅ fix: "ghost" is not a valid variant — use "secondary" */}
          <Button
            size="sm"
            variant="secondary"
            icon={<Settings size={14} />}
            onClick={() => router.push("/settings")}
          >
            Settings
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── AI ENGINEER DASHBOARD
// ─────────────────────────────────────────────────────────────────────────────

export function AiEngineerDashboard() {
  const router = useRouter();
  const [stats,   setStats]   = useState<MlDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [datasets, models, jobs] = await Promise.allSettled([
          api.get<{ datasets: MlDataset[]; total: number }>("/ml/datasets?limit=5"),
          api.get<{ versions: MlModelVersion[]; total: number }>("/ml/models?limit=5"),
          api.get<{ jobs: MlTrainingJob[]; total: number }>("/ml/jobs?limit=10"),
        ]);

        const datasetList = datasets.status === "fulfilled" ? datasets.value.data.datasets : [];
        const modelList   = models.status   === "fulfilled" ? models.value.data.versions   : [];
        const jobList     = jobs.status     === "fulfilled" ? jobs.value.data.jobs         : [];

        const activeJob = jobList.find((j) => j.status === "running") ?? null;
        const bestAcc   = modelList.reduce((acc, m) => Math.max(acc, m.accuracy), 0);

        setStats({
          total_datasets:  datasets.status === "fulfilled" ? datasets.value.data.total : datasetList.length,
          total_models:    models.status   === "fulfilled" ? models.value.data.total   : modelList.length,
          total_jobs:      jobs.status     === "fulfilled" ? jobs.value.data.total     : jobList.length,
          best_accuracy:   bestAcc,
          active_job:      activeJob,
          recent_jobs:     jobList.slice(0, 5),
          latest_versions: modelList.slice(0, 4),
          recent_datasets: datasetList.slice(0, 4),
        });
      } catch {
        setStats({
          total_datasets: 0, total_models: 0, total_jobs: 0, best_accuracy: 0,
          active_job: null, recent_jobs: [], latest_versions: [], recent_datasets: [],
        });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div className="flex justify-center py-24"><Spinner size="lg" /></div>;

  const s = stats!;

  const tiles = [
    { label: "Datasets",       value: s.total_datasets,                                    icon: <Database   size={20} className="text-cyan-400"   />, href: "/ml/datasets", raw: false },
    { label: "Model versions", value: s.total_models,                                      icon: <Layers     size={20} className="text-purple-400" />, href: "/ml/models",   raw: false },
    { label: "Training jobs",  value: s.total_jobs,                                        icon: <Cpu        size={20} className="text-blue-400"   />, href: "/ml/jobs",     raw: false },
    { label: "Best accuracy",  value: s.best_accuracy > 0 ? `${fmt(s.best_accuracy, 1)}%` : "—", icon: <TrendingUp size={20} className="text-green-400" />, href: "/ml/models",   raw: true  },
  ];

  return (
    <div className="space-y-6">

      {/* Stat tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {tiles.map((t) => (
          <StatCard
            key={t.label}
            label={t.label}
            value={t.raw ? (t.value as string) : (t.value as number)}
            icon={t.icon}
            onClick={() => router.push(t.href)}
          />
        ))}
      </div>

      {/* Active training job banner */}
      {s.active_job && (
        <div className="bg-blue-950 border border-blue-800 rounded-2xl px-5 py-4">
          <div className="flex items-start gap-3 flex-wrap">
            <div className="w-9 h-9 rounded-xl bg-blue-900 flex items-center justify-center shrink-0">
              <RefreshCw size={16} className="text-blue-400 animate-spin" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="text-blue-200 font-semibold text-sm">Training in progress</p>
                <span className="text-xs text-blue-400 bg-blue-900 px-2 py-0.5 rounded-full">
                  {s.active_job.evidence_type}
                </span>
              </div>
              <p className="text-blue-400 text-xs mt-0.5 truncate">
                {s.active_job.name} — {s.active_job.dataset_name}
              </p>
              <div className="mt-2.5 space-y-1">
                <ProgressBar pct={s.active_job.progress_pct} color="bg-blue-400" />
                <div className="flex items-center justify-between text-xs text-blue-500">
                  <span>Epoch {s.active_job.epochs_done} / {s.active_job.epochs_total}</span>
                  <span>{s.active_job.progress_pct}%</span>
                </div>
              </div>
            </div>
            <Button size="sm" variant="secondary" onClick={() => router.push("/ml/jobs")} className="shrink-0">
              View job
            </Button>
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { icon: <Upload       size={16} className="text-cyan-400"   />, label: "Upload Dataset",  desc: "Add labelled images for training",   href: "/ml/datasets", bg: "bg-cyan-950   hover:bg-cyan-900   border-cyan-900   hover:border-cyan-700"   },
          { icon: <Play         size={16} className="text-purple-400" />, label: "Train Model",     desc: "Launch a new training run",           href: "/ml/jobs",     bg: "bg-purple-950 hover:bg-purple-900 border-purple-900 hover:border-purple-700" },
          { icon: <FlaskConical size={16} className="text-green-400"  />, label: "Evaluate Model",  desc: "Run evaluation on a test set",        href: "/ml/evaluate", bg: "bg-green-950  hover:bg-green-900  border-green-900  hover:border-green-700"  },
        ].map((a) => (
          <button key={a.label} onClick={() => router.push(a.href)}
            className={`${a.bg} border rounded-2xl px-4 py-4 text-left transition-all`}>
            <div className="flex items-center gap-2 mb-1.5">
              {a.icon}
              <span className="text-sm font-semibold text-white">{a.label}</span>
            </div>
            <p className="text-xs text-gray-500">{a.desc}</p>
          </button>
        ))}
      </div>

      {/* Recent jobs + latest models */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card title="Recent Training Runs"
          action={<Link href="/ml/jobs" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">All jobs <ArrowRight size={12} /></Link>}
          padding="p-0">
          {s.recent_jobs.length === 0 ? (
            <div className="text-center py-10 px-4 space-y-2">
              <Cpu size={24} className="text-gray-700 mx-auto" />
              <p className="text-gray-600 text-sm">No training jobs yet.</p>
              <Button size="sm" icon={<Play size={13} />} onClick={() => router.push("/ml/jobs")}>Start first run</Button>
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {s.recent_jobs.map((job) => (
                <div key={job.id} className="px-4 py-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm text-white font-medium truncate">{job.name}</span>
                      <JobStatusBadge status={job.status} />
                    </div>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                      <span>{job.evidence_type}</span>
                      <span>{job.dataset_name}</span>
                      <span>{relTime(job.started_at)}</span>
                    </div>
                    {job.status === "running" && <div className="mt-1.5"><ProgressBar pct={job.progress_pct} /></div>}
                  </div>
                  <div className="text-right shrink-0">
                    {job.accuracy != null ? <AccuracyRing value={job.accuracy} size={44} /> : <span className="text-xs text-gray-600">—</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Latest Model Versions"
          action={<Link href="/ml/models" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">All versions <ArrowRight size={12} /></Link>}
          padding="p-0">
          {s.latest_versions.length === 0 ? (
            <div className="text-center py-10 px-4 space-y-2">
              <Layers size={24} className="text-gray-700 mx-auto" />
              <p className="text-gray-600 text-sm">No trained models yet.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {s.latest_versions.map((mv) => (
                <div key={mv.id} className="px-4 py-3 flex items-center gap-4">
                  <AccuracyRing value={mv.accuracy} size={48} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-white font-mono">{mv.version}</span>
                      {mv.is_active && <span className="text-xs px-2 py-0.5 rounded-full bg-green-950 text-green-400 font-medium">active</span>}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-3">
                      <span>{mv.evidence_type}</span>
                      <span>val_loss {fmt(mv.val_loss, 4)}</span>
                      <span>{relTime(mv.created_at)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Dataset activity */}
      <Card title="Dataset Activity"
        action={<Link href="/ml/datasets" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">All datasets <ArrowRight size={12} /></Link>}
        padding="p-0">
        {s.recent_datasets.length === 0 ? (
          <div className="text-center py-10 px-4 space-y-2">
            <Database size={24} className="text-gray-700 mx-auto" />
            <p className="text-gray-600 text-sm">No datasets uploaded yet.</p>
            <Button size="sm" icon={<Upload size={13} />} onClick={() => router.push("/ml/datasets")}>Upload dataset</Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr><th>Dataset</th><th>Type</th><th>Images</th><th>Size</th><th>Status</th><th>Uploaded</th></tr>
              </thead>
              <tbody>
                {s.recent_datasets.map((ds) => (
                  <tr key={ds.id}>
                    <td className="text-white font-medium">{ds.name}</td>
                    <td><span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">{ds.evidence_type}</span></td>
                    <td className="font-mono text-gray-300">{ds.image_count.toLocaleString()}</td>
                    <td className="text-gray-400 text-sm">{ds.size_mb.toFixed(1)} MB</td>
                    <td><DatasetStatusBadge status={ds.status} /></td>
                    <td className="text-gray-500 text-xs whitespace-nowrap">
                      {new Date(ds.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* GPU placeholder */}
      <div className="border border-dashed border-gray-800 rounded-2xl px-5 py-4 flex items-center gap-3">
        <Zap size={16} className="text-gray-700 shrink-0" />
        <div>
          <p className="text-gray-600 text-sm font-medium">GPU Usage</p>
          <p className="text-gray-700 text-xs mt-0.5">Live GPU monitoring will appear here once the metrics endpoint is connected.</p>
        </div>
        <span className="ml-auto text-xs text-gray-700 border border-gray-800 px-2 py-0.5 rounded-full">Phase 3</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── INVESTIGATOR DASHBOARD
// ─────────────────────────────────────────────────────────────────────────────

export function InvestigatorDashboard() {
  const router = useRouter();

  const [imgTotal, setImgTotal] = useState<number | null>(null);
  const [cmpTotal, setCmpTotal] = useState<number | null>(null);
  const [repTotal, setRepTotal] = useState<number | null>(null);
  const [recent,   setRecent]   = useState<SimilarityResponse[]>([]);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [imgs, cmps, reps] = await Promise.allSettled([
          imageService.list({ limit: 1 }),
          compareService.list({ limit: 5 }),
          reportService.list({ limit: 1 }),
        ]);
        if (imgs.status === "fulfilled") setImgTotal(imgs.value.total);
        if (cmps.status === "fulfilled") { setCmpTotal(cmps.value.total); setRecent(cmps.value.results); }
        if (reps.status === "fulfilled") setRepTotal(reps.value.total);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const stats = [
    { label: "Images uploaded",    value: imgTotal, icon: <Upload     size={20} className="text-blue-400"   />, href: "/upload"  },
    { label: "Comparisons run",    value: cmpTotal, icon: <GitCompare size={20} className="text-purple-400" />, href: "/compare" },
    { label: "Reports generated",  value: repTotal, icon: <FileText   size={20} className="text-green-400"  />, href: "/reports" },
    { label: "Recent sessions",    value: recent.length, icon: <Clock size={20} className="text-yellow-400"  />, href: "/logs"    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={loading ? null : (s.value ?? 0)}
            icon={s.icon} onClick={() => router.push(s.href)} />
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { icon: <Upload    size={16} className="text-blue-400"   />, label: "Upload Evidence",  desc: "Add fingerprint or toolmark images",    href: "/upload",  bg: "bg-blue-950   hover:bg-blue-900   border-blue-900   hover:border-blue-700"   },
          { icon: <GitCompare size={16} className="text-purple-400" />, label: "Run Comparison",  desc: "AI-assisted similarity analysis",         href: "/compare", bg: "bg-purple-950 hover:bg-purple-900 border-purple-900 hover:border-purple-700" },
          { icon: <FileText  size={16} className="text-green-400"  />, label: "Generate Report", desc: "Export findings to PDF",                  href: "/reports", bg: "bg-green-950  hover:bg-green-900  border-green-900  hover:border-green-700"  },
        ].map((a) => (
          <button key={a.label} onClick={() => router.push(a.href)}
            className={`${a.bg} border rounded-2xl px-4 py-4 text-left transition-all`}>
            <div className="flex items-center gap-2 mb-1.5">
              {a.icon}
              <span className="text-sm font-semibold text-white">{a.label}</span>
            </div>
            <p className="text-xs text-gray-500">{a.desc}</p>
          </button>
        ))}
      </div>

      {/* Recent comparisons */}
      <Card title="Recent Comparisons"
        action={<Link href="/compare" className="flex items-center gap-1 text-blue-400 hover:text-blue-300 text-sm transition-colors">View all <ArrowRight size={14} /></Link>}>
        {loading ? (
          <div className="flex justify-center py-10"><Spinner size="md" /></div>
        ) : recent.length === 0 ? (
          <div className="text-center py-12 space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
              <GitCompare size={24} className="text-gray-600" />
            </div>
            <div>
              <p className="text-gray-400 text-sm font-medium">No comparisons yet</p>
              <p className="text-gray-600 text-xs mt-1">Upload two evidence images and run your first analysis.</p>
            </div>
            <Button size="sm" icon={<GitCompare size={14} />} onClick={() => router.push("/compare")}>Run first comparison</Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr><th>Query image</th><th>Reference image</th><th>Type</th><th>Similarity</th><th>Result</th><th>Date</th></tr>
              </thead>
              <tbody>
                {recent.map((r) => (
                  <tr key={r.id}>
                    <td><span className="block truncate max-w-[130px] text-white" title={r.image_1?.original_filename}>{r.image_1?.original_filename ?? `#${r.id}`}</span></td>
                    <td><span className="block truncate max-w-[130px]" title={r.image_2?.original_filename}>{r.image_2?.original_filename ?? "—"}</span></td>
                    <td>{r.image_1 ? <EvidenceBadge type={r.image_1.evidence_type} /> : <span className="text-gray-600">—</span>}</td>
                    <td className="font-mono text-white">{r.similarity_percentage.toFixed(1)}%</td>
                    <td><MatchBadge status={r.match_status} /></td>
                    <td className="text-gray-500 text-xs whitespace-nowrap">
                      {new Date(r.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── ADMIN DASHBOARD
// ─────────────────────────────────────────────────────────────────────────────

function AdminDashboard() {
  const router = useRouter();
  const [health, setHealth] = useState<{
    status: string; active_sessions: number; requests_today: number; error_rate_pct: number;
  } | null>(null);

  useEffect(() => {
    api.get("/admin/health")
      .then(({ data }) => setHealth({
        status:          data.status,
        active_sessions: data.metrics?.active_sessions ?? 0,
        requests_today:  data.metrics?.requests_today  ?? 0,
        error_rate_pct:  data.metrics?.error_rate_pct  ?? 0,
      }))
      .catch(() => {});
  }, []);

  const healthColor = !health ? "text-gray-500"
    : health.status === "healthy"  ? "text-green-400"
    : health.status === "degraded" ? "text-yellow-400"
    : "text-red-400";

  return (
    <div className="space-y-8">
      {/* System health strip */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl px-5 py-3 flex items-center gap-5 flex-wrap">
        <div className="flex items-center gap-2">
          <Server size={14} className="text-gray-500" />
          <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">System</span>
          {health ? (
            <span className={`text-xs font-semibold ${healthColor}`}>{health.status}</span>
          ) : (
            <Spinner size="sm" />
          )}
        </div>
        <div className="h-4 w-px bg-gray-800" />
        <div className="flex items-center gap-4 text-xs text-gray-500 flex-wrap">
          <span><span className="text-white font-mono">{health?.active_sessions ?? "—"}</span> active sessions</span>
          <span><span className="text-white font-mono">{health?.requests_today?.toLocaleString() ?? "—"}</span> requests today</span>
          <span>
            <span className={(health?.error_rate_pct ?? 0) > 1 ? "text-red-400 font-mono" : "text-green-400 font-mono"}>
              {health?.error_rate_pct ?? "—"}%
            </span> error rate
          </span>
        </div>
        <button onClick={() => router.push("/admin")}
          className="ml-auto flex items-center gap-1.5 text-xs text-gray-500 hover:text-white transition-colors">
          <Shield size={13} />Admin panel<ChevronRight size={12} />
        </button>
      </div>

      {/* Investigator section */}
      <div>
        <SectionHeader title="Investigator Overview"
          action={<span className="text-xs text-gray-600 flex items-center gap-1"><Users size={11} /> analysts & investigators</span>} />
        <InvestigatorDashboard />
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-800" /></div>
        <div className="relative flex justify-center">
          <span className="bg-black px-4 text-xs text-gray-600 uppercase tracking-widest">ML Operations</span>
        </div>
      </div>

      {/* AI Engineer section */}
      <div>
        <SectionHeader title="AI / ML Operations"
          action={<span className="text-xs text-gray-600 flex items-center gap-1"><Cpu size={11} /> model training & evaluation</span>} />
        <AiEngineerDashboard />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── PAGE ROOT — role router
// ─────────────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();

  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  const subtitle: Record<string, string> = {
    admin:       "System administration & full operations overview",
    ai_engineer: "ML operations — training, evaluation, model versioning",
    analyst:     "ForensicEdge AI-Assisted Evidence Analysis",
  };

  const role = user?.role ?? "analyst";

  return (
    <>
      <Head><title>Dashboard — ForensicEdge</title></Head>

      <AppLayout title="Dashboard">
        <div className="space-y-6">

          {/* Fix: ProfileManagementCard is now INSIDE the JSX return,
               rendered for every role — not a dead bare call outside JSX. */}
          <ProfileManagementCard />

          {/* Welcome heading */}
          <div>
            <h2 className="text-white text-xl font-semibold">
              Welcome back, <span className="text-blue-400">{firstName}</span>
            </h2>
            <p className="text-gray-500 text-sm mt-1">
              {subtitle[role] ?? subtitle.analyst}
            </p>
          </div>

          {/* Role-specific content */}
          {role === "admin"       && <AdminDashboard />}
          {role === "ai_engineer" && <AiEngineerDashboard />}
          {(role === "analyst" || !["admin", "ai_engineer"].includes(role)) && (
            <InvestigatorDashboard />
          )}

        </div>
      </AppLayout>
    </>
  );
}