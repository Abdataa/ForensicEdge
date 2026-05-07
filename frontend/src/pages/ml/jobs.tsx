/**
 * src/pages/ml/jobs.tsx
 * ──────────────────────
 * AI Engineer — Training Job Management
 *
 * Features
 * ─────────
 *   • List all training jobs with live status + progress bars
 *   • Launch new training run (select dataset + epochs + hyperparameters)
 *   • Live polling every 3 s for any running job
 *   • Cancel queued/running jobs
 *   • Drill-down job detail drawer (config, error message, metrics)
 *   • Filter by evidence_type and status
 *
 * API
 * ───
 *   GET  /ml/jobs           mlService.listJobs()
 *   POST /ml/jobs           mlService.launchJob()
 *   GET  /ml/jobs/:id       mlService.getJob()
 *   POST /ml/jobs/:id/cancel mlService.cancelJob()
 */

import { useState, useEffect, useCallback, FormEvent } from "react";
import Head from "next/head";
import {
  Play, XCircle, CheckCircle, Clock, RefreshCw,
  ChevronUp, Plus, Cpu, AlertTriangle, ChevronDown,
  Settings, BarChart2, Database,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx  from "clsx";

import AppLayout from "../../components/layout/AppLayout";
import Card      from "../../components/ui/Card";
import Button    from "../../components/ui/Button";
import Input     from "../../components/ui/Input";
import Spinner   from "../../components/ui/Spinner";
import { mlService, MlTrainingJob, MlDataset } from "../../services/mlService";

// ─────────────────────────────────────────────────────────────────────────────
// Shared constants + helpers
// ─────────────────────────────────────────────────────────────────────────────

const STATUS_CFG = {
  queued:    { icon: <Clock    size={12} />, cls: "bg-gray-800   text-gray-400",  bar: "bg-gray-600"  },
  running:   { icon: <RefreshCw size={12} className="animate-spin" />, cls: "bg-blue-950  text-blue-400",  bar: "bg-blue-500"  },
  completed: { icon: <CheckCircle size={12} />, cls: "bg-green-950 text-green-400", bar: "bg-green-500" },
  failed:    { icon: <XCircle  size={12} />, cls: "bg-red-950   text-red-400",   bar: "bg-red-500"   },
} as const;

function JobBadge({ status }: { status: MlTrainingJob["status"] }) {
  const cfg = STATUS_CFG[status];
  return (
    <span className={clsx("inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium", cfg.cls)}>
      {cfg.icon} {status}
    </span>
  );
}

function ProgressBar({ pct, status }: { pct: number; status: MlTrainingJob["status"] }) {
  const color = STATUS_CFG[status].bar;
  return (
    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div
        className={clsx("h-full rounded-full transition-all duration-700", color)}
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  );
}

function AccuracyRing({ value, size = 52 }: { value: number; size?: number }) {
  const r     = (size - 8) / 2;
  const circ  = 2 * Math.PI * r;
  const pct   = Math.min(100, Math.max(0, value));
  const dash  = (pct / 100) * circ;
  const color = pct >= 90 ? "#4ade80" : pct >= 75 ? "#facc15" : "#f87171";
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1f2937" strokeWidth={6} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-bold text-white">{pct.toFixed(0)}%</span>
      </div>
    </div>
  );
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

function duration(start: string | null, end: string | null) {
  if (!start) return "—";
  const endTs  = end ? new Date(end).getTime() : Date.now();
  const secs   = Math.floor((endTs - new Date(start).getTime()) / 1000);
  if (secs < 60)  return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Job detail drawer
// ─────────────────────────────────────────────────────────────────────────────

function JobDetailDrawer({ job, onClose }: { job: MlTrainingJob; onClose: () => void }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-white font-semibold">{job.name}</h3>
          <p className="text-gray-500 text-sm">{job.evidence_type} · {job.dataset_name}</p>
        </div>
        <button type="button" onClick={onClose} className="text-gray-600 hover:text-white transition-colors" aria-label="Close">
          <ChevronUp size={18} />
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Status",     value: <JobBadge status={job.status} /> },
          { label: "Progress",   value: `${job.progress_pct}%` },
          { label: "Epochs",     value: `${job.epochs_done} / ${job.epochs_total}` },
          { label: "Duration",   value: duration(job.started_at, job.finished_at) },
        ].map((s) => (
          <div key={s.label} className="bg-gray-800 rounded-xl px-3 py-2.5">
            <p className="text-xs text-gray-500 mb-1">{s.label}</p>
            {typeof s.value === "string"
              ? <p className="text-white font-mono text-sm font-medium">{s.value}</p>
              : s.value}
          </div>
        ))}
      </div>

      {/* Live metrics */}
      {(job.accuracy != null || job.val_loss != null) && (
        <div className="grid grid-cols-2 gap-3">
          {job.accuracy != null && (
            <div className="bg-gray-800 rounded-xl p-3 flex items-center gap-3">
              <AccuracyRing value={job.accuracy} size={48} />
              <div>
                <p className="text-xs text-gray-500">Accuracy</p>
                <p className="text-white font-semibold">{job.accuracy.toFixed(2)}%</p>
              </div>
            </div>
          )}
          {job.val_loss != null && (
            <div className="bg-gray-800 rounded-xl p-3">
              <p className="text-xs text-gray-500 mb-1">Validation loss</p>
              <p className="text-white font-semibold font-mono">{job.val_loss.toFixed(4)}</p>
            </div>
          )}
        </div>
      )}

      {/* Config */}
      {job.config && Object.keys(job.config).length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Settings size={11} /> Hyperparameters
          </p>
          <div className="bg-gray-800 rounded-xl p-3">
            <pre className="text-xs text-gray-300 whitespace-pre-wrap">
              {JSON.stringify(job.config, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Error */}
      {job.error_message && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3">
          <p className="text-xs text-red-400 font-medium mb-1 flex items-center gap-1.5">
            <AlertTriangle size={11} /> Error
          </p>
          <p className="text-xs text-red-500 whitespace-pre-wrap">{job.error_message}</p>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Launch form
// ─────────────────────────────────────────────────────────────────────────────

function LaunchForm({
  datasets,
  onSuccess,
  onCancel,
}: {
  datasets:  MlDataset[];
  onSuccess: () => void;
  onCancel:  () => void;
}) {
  const readyDatasets = datasets.filter((d) => d.status === "ready");

  const [name,         setName]         = useState("");
  const [evidenceType, setEvidenceType] = useState<"fingerprint" | "toolmark">("fingerprint");
  const [datasetId,    setDatasetId]    = useState<number | "">("");
  const [epochs,       setEpochs]       = useState("50");
  const [lr,           setLr]           = useState("0.001");
  const [batchSize,    setBatchSize]    = useState("32");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [launching,    setLaunching]    = useState(false);
  const [error,        setError]        = useState("");

  // Filter datasets to match selected evidence type
  const filteredDatasets = readyDatasets.filter((d) => d.evidence_type === evidenceType);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!datasetId) { setError("Please select a dataset."); return; }
    setError("");
    setLaunching(true);
    try {
      await mlService.launchJob({
        name:          name.trim(),
        evidence_type: evidenceType,
        dataset_id:    Number(datasetId),
        epochs:        Number(epochs),
        config: {
          lr:         parseFloat(lr),
          batch_size: parseInt(batchSize),
        },
      });
      toast.success("Training job launched!");
      onSuccess();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Could not launch job.";
      setError(detail);
    } finally {
      setLaunching(false);
    }
  };

  return (
    <Card title="Launch training run">
      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm mb-4">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Run name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="fingerprint-resnet-v3"
            required
            minLength={2}
            disabled={launching}
          />
          <div className="space-y-1.5">
            <label htmlFor="evidence-type"   className="field-label">Evidence type</label>
            <select
              id="evidence-type"
              value={evidenceType}
              onChange={(e) => {
                setEvidenceType(e.target.value as "fingerprint" | "toolmark");
                setDatasetId("");
              }}
              disabled={launching}
              className="field"
            >
              <option value="fingerprint">Fingerprint</option>
              <option value="toolmark">Toolmark</option>
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="dataset-select" className="field-label">Dataset</label>
          <select
            id ="dataset-select"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value ? Number(e.target.value) : "")}
            disabled={launching}
            required
            className="field"
          >
            <option value="">
              {filteredDatasets.length === 0
                ? `No ready ${evidenceType} datasets — upload one first`
                : "Select a dataset…"}
            </option>
            {filteredDatasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.image_count.toLocaleString()} images)
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Input
            label="Epochs"
            type="number"
            value={epochs}
            onChange={(e) => setEpochs(e.target.value)}
            min="1"
            max="1000"
            disabled={launching}
          />
        </div>

        {/* Advanced config */}
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          <Settings size={13} />
          Advanced hyperparameters
          <ChevronDown size={13} className={clsx("transition-transform", showAdvanced && "rotate-180")} />
        </button>

        {showAdvanced && (
          <div className="bg-gray-900 rounded-xl p-4 space-y-4 border border-gray-800">
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Learning rate"
                type="number"
                value={lr}
                onChange={(e) => setLr(e.target.value)}
                step="0.0001"
                min="0.0001"
                max="1"
                disabled={launching}
              />
              <Input
                label="Batch size"
                type="number"
                value={batchSize}
                onChange={(e) => setBatchSize(e.target.value)}
                min="8"
                max="512"
                step="8"
                disabled={launching}
              />
            </div>
            <p className="text-xs text-gray-600">
              These values are passed directly to the training engine as the{" "}
              <code className="text-gray-500">config</code> dict.
            </p>
          </div>
        )}

        <div className="flex items-center gap-3">
          <Button type="submit" loading={launching} icon={<Play size={14} />}>
            {launching ? "Launching…" : "Launch training"}
          </Button>
          <Button type="button" variant="secondary" onClick={onCancel} disabled={launching}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function JobsPage() {
  const [jobs,        setJobs]        = useState<MlTrainingJob[]>([]);
  const [datasets,    setDatasets]    = useState<MlDataset[]>([]);
  const [total,       setTotal]       = useState(0);
  const [loading,     setLoading]     = useState(true);
  const [showForm,    setShowForm]    = useState(false);
  const [cancelId,    setCancelId]    = useState<number | null>(null);
  const [expandedId,  setExpandedId]  = useState<number | null>(null);
  const [etFilter,    setEtFilter]    = useState("");
  const [stFilter,    setStFilter]    = useState("");

  const hasRunning = jobs.some((j) => j.status === "running" || j.status === "queued");

  const loadJobs = useCallback(async () => {
    try {
      const [jobsRes, dsRes] = await Promise.allSettled([
        mlService.listJobs({ limit: 50,
          ...(etFilter && { evidence_type: etFilter }),
          ...(stFilter && { status: stFilter }),
        }),
        mlService.listDatasets({ limit: 100 }),
      ]);
      if (jobsRes.status === "fulfilled") {
        setJobs(jobsRes.value.jobs);
        setTotal(jobsRes.value.total);
      }
      if (dsRes.status === "fulfilled") setDatasets(dsRes.value.datasets);
    } catch {
      toast.error("Could not load training jobs.");
    } finally {
      setLoading(false);
    }
  }, [etFilter, stFilter]);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  // Live polling while any job is running/queued
  useEffect(() => {
    if (!hasRunning) return;
    const id = setInterval(loadJobs, 3000);
    return () => clearInterval(id);
  }, [hasRunning, loadJobs]);

  const handleCancel = async (job: MlTrainingJob) => {
    if (!confirm(`Cancel job "${job.name}"?`)) return;
    setCancelId(job.id);
    try {
      await mlService.cancelJob(job.id);
      toast.success("Job cancelled.");
      await loadJobs();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Cancel failed.";
      toast.error(detail);
    } finally {
      setCancelId(null);
    }
  };

  return (
    <>
      <Head><title>Training Jobs — ForensicEdge ML</title></Head>
      <AppLayout title="Training Jobs" requiredRole="ai_engineer">
        <div className="space-y-5">

          {/* Header */}
          <div className="flex items-end justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-white font-semibold text-lg">Training Jobs</h2>
              <p className="text-gray-500 text-sm mt-0.5">
                {loading ? "Loading…" : `${total} job${total !== 1 ? "s" : ""}`}
                {hasRunning && (
                  <span className="ml-2 text-blue-400 inline-flex items-center gap-1">
                    <RefreshCw size={11} className="animate-spin" /> live
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm" variant="secondary"
                icon={<RefreshCw size={13} className={loading ? "animate-spin" : ""} />}
                onClick={loadJobs} disabled={loading}
              >Refresh</Button>
              <Button
                size="sm"
                icon={showForm ? <ChevronUp size={14} /> : <Plus size={14} />}
                onClick={() => setShowForm((v) => !v)}
              >
                {showForm ? "Cancel" : "Launch job"}
              </Button>
            </div>
          </div>

          {/* Launch form */}
          {showForm && (
            <LaunchForm
              datasets={datasets}
              onSuccess={() => { setShowForm(false); loadJobs(); }}
              onCancel={() => setShowForm(false)}
            />
          )}

          {/* Filters */}
          <Card>
            <div className="flex items-center gap-3 flex-wrap">
              <select value={etFilter} onChange={(e) => setEtFilter(e.target.value)}
                className="field text-sm min-w-[160px]" aria-label="Filter by type">
                <option value="">All types</option>
                <option value="fingerprint">Fingerprint</option>
                <option value="toolmark">Toolmark</option>
              </select>
              <select value={stFilter} onChange={(e) => setStFilter(e.target.value)}
                className="field text-sm min-w-[160px]" aria-label="Filter by status">
                <option value="">All statuses</option>
                <option value="queued">Queued</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
              {(etFilter || stFilter) && (
                <Button size="sm" variant="secondary"
                  onClick={() => { setEtFilter(""); setStFilter(""); }}>
                  Clear
                </Button>
              )}
            </div>
          </Card>

          {/* Job list */}
          {loading ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : jobs.length === 0 ? (
            <Card className="text-center py-16 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
                <Cpu size={28} className="text-gray-600" />
              </div>
              <div>
                <p className="text-gray-400 text-sm font-medium">No training jobs yet</p>
                <p className="text-gray-600 text-xs mt-1">
                  Upload a dataset first, then launch a training run.
                </p>
              </div>
              <Button size="sm" icon={<Play size={13} />} onClick={() => setShowForm(true)}>
                Launch first job
              </Button>
            </Card>
          ) : (
            <div className="space-y-2">
              {jobs.map((job) => (
                <div key={job.id} className="border border-gray-800 rounded-2xl overflow-hidden">

                  {/* Job row */}
                  <div
                    className="flex items-center gap-4 bg-gray-900 px-4 py-3 cursor-pointer hover:bg-gray-850 transition-colors"
                    onClick={() => setExpandedId(expandedId === job.id ? null : job.id)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-white font-medium text-sm">{job.name}</span>
                        <JobBadge status={job.status} />
                        <span className="text-xs text-gray-600">{job.evidence_type}</span>
                        <span className="text-xs text-gray-700 flex items-center gap-0.5">
                          <Database size={10} /> {job.dataset_name}
                        </span>
                      </div>

                      {/* Progress bar */}
                      <div className="mt-2 space-y-1">
                        <ProgressBar pct={job.progress_pct} status={job.status} />
                        <div className="flex items-center justify-between text-xs text-gray-600">
                          <span>
                            Epoch {job.epochs_done}/{job.epochs_total}
                            {job.status === "running" && ` · ${job.progress_pct}%`}
                          </span>
                          <span>{relTime(job.started_at)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Accuracy ring */}
                    <div className="shrink-0">
                      {job.accuracy != null
                        ? <AccuracyRing value={job.accuracy} size={48} />
                        : (
                          <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center">
                            <BarChart2 size={16} className="text-gray-600" />
                          </div>
                        )}
                    </div>

                    {/* Cancel button */}
                    {(job.status === "queued" || job.status === "running") && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleCancel(job); }}
                        disabled={cancelId === job.id}
                        title="Cancel job"
                        className="shrink-0 p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-gray-800 transition-colors"
                      >
                        {cancelId === job.id ? <Spinner size="sm" /> : <XCircle size={15} />}
                      </button>
                    )}

                    <ChevronDown
                      size={15}
                      className={clsx(
                        "text-gray-600 shrink-0 transition-transform",
                        expandedId === job.id && "rotate-180"
                      )}
                    />
                  </div>

                  {/* Detail drawer */}
                  {expandedId === job.id && (
                    <div className="border-t border-gray-800 p-4">
                      <JobDetailDrawer job={job} onClose={() => setExpandedId(null)} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </AppLayout>
    </>
  );
}