/**
 * src/pages/ml/evaluate.tsx
 * ──────────────────────────
 * AI Engineer — Model Evaluation
 *
 * Features
 * ─────────
 *   • Run evaluation: select model version + evaluation dataset
 *   • View results: accuracy, val_loss, precision, recall, F1, FMR, FNMR, EER
 *   • History of all past evaluations (paginated)
 *   • Compare multiple evaluation runs visually
 *   • Filter by model or evidence type
 *
 * API
 * ───
 *   GET  /ml/evaluate          mlService.listEvaluations()
 *   POST /ml/evaluate          mlService.runEvaluation()
 *   GET  /ml/evaluate/:id      mlService.getEvaluation()
 *   GET  /ml/models            mlService.listModels()
 *   GET  /ml/datasets          mlService.listDatasets()
 */

import { useState, useEffect, useCallback, FormEvent } from "react";
import Head from "next/head";
import {
  FlaskConical, CheckCircle, ChevronUp, Plus,
  RefreshCw, BarChart2, TrendingUp, Target,
  Activity, AlertTriangle, Info,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx  from "clsx";

import AppLayout from "../../components/layout/AppLayout";
import Card      from "../../components/ui/Card";
import Button    from "../../components/ui/Button";
import Spinner   from "../../components/ui/Spinner";
import {
  mlService,
  MlEvaluationResult,
  MlModelVersion,
  MlDataset,
} from "../../services/mlService";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, d = 2): string {
  if (n == null) return "—";
  return n.toFixed(d);
}

function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Metric bar (horizontal gauge)
// ─────────────────────────────────────────────────────────────────────────────

function MetricBar({
  label,
  value,
  max = 100,
  unit = "%",
  invert = false,        // lower is better (for loss / error rates)
  description,
}: {
  label:       string;
  value:       number | null | undefined;
  max?:        number;
  unit?:       string;
  invert?:     boolean;
  description?: string;
}) {
  const pct   = value != null ? Math.min(100, (value / max) * 100) : 0;
  const good  = value != null ? (invert ? value < max * 0.1 : value >= max * 0.85) : false;
  const color = value == null ? "bg-gray-700"
    : good    ? "bg-green-500"
    : value < (invert ? max * 0.3 : max * 0.6) ? "bg-red-500"
    : "bg-yellow-500";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-gray-300 font-medium">{label}</span>
          {description && (
            <span title={description}>
              <Info size={11} className="text-gray-600" />
            </span>
          )}
        </div>
        <span className={clsx("text-sm font-mono font-semibold", good ? "text-green-400" : "text-gray-300")}>
          {value != null ? `${fmt(value, 2)}${unit}` : "—"}
        </span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Evaluation result card
// ─────────────────────────────────────────────────────────────────────────────

function EvaluationCard({
  ev,
  models,
  datasets,
}: {
  ev:       MlEvaluationResult;
  models:   MlModelVersion[];
  datasets: MlDataset[];
}) {
  const [expanded, setExpanded] = useState(false);

  const model   = models.find((m) => m.id === ev.model_id);
  const dataset = datasets.find((d) => d.id === ev.dataset_id);
  const details = ev.details ?? {};

  const grade =
    ev.accuracy >= 95 ? { label: "Excellent", cls: "bg-green-950  text-green-400"  }
    : ev.accuracy >= 85 ? { label: "Good",      cls: "bg-blue-950   text-blue-400"   }
    : ev.accuracy >= 70 ? { label: "Fair",      cls: "bg-yellow-950 text-yellow-400" }
    :                     { label: "Poor",      cls: "bg-red-950    text-red-400"    };

  return (
    <div className="border border-gray-800 rounded-2xl bg-gray-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-start gap-4 px-5 py-4">
        {/* Accuracy circle */}
        <div className="w-16 h-16 rounded-2xl bg-gray-800 flex flex-col items-center justify-center shrink-0">
          <span className={clsx("text-xs font-bold", ev.accuracy >= 85 ? "text-green-400" : ev.accuracy >= 70 ? "text-yellow-400" : "text-red-400")}>
            {fmt(ev.accuracy, 1)}%
          </span>
          <span className="text-xs text-gray-600 mt-0.5">acc</span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-white font-medium text-sm">
              {model?.version ?? `Model #${ev.model_id}`}
            </span>
            <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", grade.cls)}>
              {grade.label}
            </span>
            <span className={clsx(
              "text-xs px-2 py-0.5 rounded-full",
              ev.evidence_type === "fingerprint" ? "bg-purple-950 text-purple-400" : "bg-cyan-950 text-cyan-400"
            )}>
              {ev.evidence_type}
            </span>
          </div>

          <p className="text-gray-500 text-xs mt-0.5">
            Evaluated on:{" "}
            <span className="text-gray-400">{dataset?.name ?? `Dataset #${ev.dataset_id}`}</span>
            {" · "}{relTime(ev.created_at)}
          </p>

          {/* Quick metric row */}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {[
              { label: "Precision", value: ev.precision },
              { label: "Recall",    value: ev.recall    },
              { label: "F1",        value: ev.f1_score  },
            ].map((m) => (
              <div key={m.label} className="text-xs">
                <span className="text-gray-600">{m.label}: </span>
                <span className={clsx(
                  "font-mono font-medium",
                  m.value >= 85 ? "text-green-400" : m.value >= 70 ? "text-yellow-400" : "text-red-400"
                )}>
                  {fmt(m.value, 2)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-gray-600 hover:text-white transition-colors shrink-0"
        >
          {expanded ? <ChevronUp size={15} /> : <BarChart2 size={15} />}
        </button>
      </div>

      {/* Expanded metrics */}
      {expanded && (
        <div className="border-t border-gray-800 px-5 py-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
            <MetricBar label="Accuracy"        value={ev.accuracy}           description="Overall correct classifications" />
            <MetricBar label="Precision"       value={ev.precision}          description="TP / (TP + FP)" />
            <MetricBar label="Recall"          value={ev.recall}             description="TP / (TP + FN)" />
            <MetricBar label="F1 Score"        value={ev.f1_score}           description="Harmonic mean of precision and recall" />
            <MetricBar label="FMR (False Match Rate)"   value={typeof details.fmr === "number" ? details.fmr * 100 : null} description="Rate of incorrect matches" invert />
            <MetricBar label="FNMR (False Non-Match)"   value={typeof details.fnmr === "number" ? details.fnmr * 100 : null} description="Rate of missed matches"    invert />
            <MetricBar label="EER (Equal Error Rate)"   value={typeof details.eer === "number" ? details.eer * 100 : null} description="Point where FMR = FNMR"    invert />
          </div>

          {/* Note from evaluation engine */}
          {typeof details.note === "string" && details.note.length > 0 && (
            <div className="bg-yellow-950 border border-yellow-800 rounded-xl px-4 py-3">
              <p className="text-xs text-yellow-400 flex items-center gap-1.5 mb-1">
                <AlertTriangle size={11} /> Note
              </p>
              <p className="text-xs text-yellow-500">{details.note}</p>
            </div>
          )}

          {/* Full details JSON for engineers */}
          {Object.keys(details).filter((k) => !["note", "fmr", "fnmr", "eer"].includes(k)).length > 0 && (
            <div>
              <p className="text-xs text-gray-600 mb-1.5">Additional details</p>
              <div className="bg-gray-800 rounded-xl p-3 overflow-x-auto">
                <pre className="text-xs text-gray-400 whitespace-pre-wrap">
                  {JSON.stringify(details, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Run evaluation form
// ─────────────────────────────────────────────────────────────────────────────

function EvaluationForm({
  models,
  datasets,
  onSuccess,
  onCancel,
}: {
  models:    MlModelVersion[];
  datasets:  MlDataset[];
  onSuccess: () => void;
  onCancel:  () => void;
}) {
  const [modelId,   setModelId]   = useState<number | "">("");
  const [datasetId, setDatasetId] = useState<number | "">("");
  const [running,   setRunning]   = useState(false);
  const [error,     setError]     = useState("");

  // Filter datasets to match selected model's evidence type
  const selectedModel = models.find((m) => m.id === Number(modelId));
  const compatibleDs  = selectedModel
    ? datasets.filter((d) => d.evidence_type === selectedModel.evidence_type && d.status === "ready")
    : datasets.filter((d) => d.status === "ready");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!modelId || !datasetId) { setError("Select both a model and a dataset."); return; }
    setError("");
    setRunning(true);
    try {
      await mlService.runEvaluation({
        model_id:   Number(modelId),
        dataset_id: Number(datasetId),
      });
      toast.success("Evaluation complete.");
      onSuccess();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Evaluation failed.";
      setError(detail);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card title="Run model evaluation">
      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm mb-4">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Model selector */}
          <div className="space-y-1.5">
            <label htmlFor="model-select" className="field-label">Model version</label>
            <select
              id="model-select"
              value={modelId}
              onChange={(e) => { setModelId(e.target.value ? Number(e.target.value) : ""); setDatasetId(""); }}
              disabled={running}
              required
              className="field"
            >
              <option value="">Select a model…</option>
              {["fingerprint", "toolmark"].map((et) => {
                const group = models.filter((m) => m.evidence_type === et);
                if (group.length === 0) return null;
                return (
                  <optgroup key={et} label={et.charAt(0).toUpperCase() + et.slice(1)}>
                    {group.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.version} — {m.accuracy.toFixed(1)}% acc{m.is_active ? " ★ active" : ""}
                      </option>
                    ))}
                  </optgroup>
                );
              })}
            </select>
          </div>

          {/* Dataset selector */}
          <div className="space-y-1.5">
            <label htmlFor="dataset-select" className="field-label">Evaluation dataset</label>
            <select
              id="dataset-select"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value ? Number(e.target.value) : "")}
              disabled={running || !modelId}
              required
              className="field"
            >
              <option value="">
                {!modelId
                  ? "Select a model first"
                  : compatibleDs.length === 0
                  ? `No ready ${selectedModel?.evidence_type} datasets`
                  : "Select a dataset…"}
              </option>
              {compatibleDs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.image_count.toLocaleString()} images)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Info box */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-gray-500 space-y-1">
          <p className="text-gray-400 font-medium">Metrics computed</p>
          <p>Accuracy · Precision · Recall · F1 Score · FMR · FNMR · EER</p>
          <p className="text-gray-600">
            Use a held-out test set, not the same dataset used for training.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button type="submit" loading={running} icon={<FlaskConical size={14} />}>
            {running ? "Evaluating…" : "Run evaluation"}
          </Button>
          <Button type="button" variant="secondary" onClick={onCancel} disabled={running}>
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

export default function EvaluatePage() {
  const [evaluations, setEvaluations] = useState<MlEvaluationResult[]>([]);
  const [models,      setModels]      = useState<MlModelVersion[]>([]);
  const [datasets,    setDatasets]    = useState<MlDataset[]>([]);
  const [total,       setTotal]       = useState(0);
  const [loading,     setLoading]     = useState(true);
  const [showForm,    setShowForm]    = useState(false);

  const load = useCallback(async () => {
    try {
      const [evRes, modelRes, dsRes] = await Promise.allSettled([
        mlService.listEvaluations({ limit: 50 }),
        mlService.listModels({ limit: 100 }),
        mlService.listDatasets({ limit: 100 }),
      ]);
      if (evRes.status    === "fulfilled") { setEvaluations(evRes.value.evaluations); setTotal(evRes.value.total); }
      if (modelRes.status === "fulfilled") setModels(modelRes.value.versions);
      if (dsRes.status    === "fulfilled") setDatasets(dsRes.value.datasets);
    } catch {
      toast.error("Could not load evaluations.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Summary stats from evaluations
  const bestAcc  = evaluations.length ? Math.max(...evaluations.map((e) => e.accuracy)) : null;
  const avgAcc   = evaluations.length
    ? evaluations.reduce((a, e) => a + e.accuracy, 0) / evaluations.length
    : null;
  const latestEv = evaluations[0] ?? null;

  return (
    <>
      <Head><title>Model Evaluation — ForensicEdge ML</title></Head>
      <AppLayout title="Model Evaluation" requiredRole="ai_engineer">
        <div className="space-y-6">

          {/* Header */}
          <div className="flex items-end justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-white font-semibold text-lg">Model Evaluation</h2>
              <p className="text-gray-500 text-sm mt-0.5">
                {loading ? "Loading…" : `${total} evaluation${total !== 1 ? "s" : ""} run`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm" variant="secondary"
                icon={<RefreshCw size={13} className={loading ? "animate-spin" : ""} />}
                onClick={load} disabled={loading}
              >Refresh</Button>
              <Button
                size="sm"
                icon={showForm ? <ChevronUp size={14} /> : <Plus size={14} />}
                onClick={() => setShowForm((v) => !v)}
              >
                {showForm ? "Cancel" : "Run evaluation"}
              </Button>
            </div>
          </div>

          {/* Evaluation form */}
          {showForm && (
            <EvaluationForm
              models={models}
              datasets={datasets}
              onSuccess={() => { setShowForm(false); load(); }}
              onCancel={() => setShowForm(false)}
            />
          )}

          {/* Summary stat strip */}
          {evaluations.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                {
                  label: "Total runs",
                  value: total,
                  icon:  <FlaskConical size={15} className="text-blue-400" />,
                },
                {
                  label: "Best accuracy",
                  value: bestAcc != null ? `${bestAcc.toFixed(1)}%` : "—",
                  icon:  <TrendingUp size={15} className="text-green-400" />,
                },
                {
                  label: "Average accuracy",
                  value: avgAcc != null ? `${avgAcc.toFixed(1)}%` : "—",
                  icon:  <BarChart2 size={15} className="text-purple-400" />,
                },
                {
                  label: "Latest F1",
                  value: latestEv ? `${latestEv.f1_score.toFixed(1)}%` : "—",
                  icon:  <Target size={15} className="text-yellow-400" />,
                },
              ].map((s) => (
                <div key={s.label} className="bg-gray-900 rounded-xl p-4 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center shrink-0">
                    {s.icon}
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">{s.label}</p>
                    <p className="text-white font-semibold text-lg leading-tight">{s.value}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Evaluation list */}
          {loading ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : evaluations.length === 0 ? (
            <Card className="text-center py-16 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
                <FlaskConical size={28} className="text-gray-600" />
              </div>
              <div>
                <p className="text-gray-400 text-sm font-medium">No evaluations run yet</p>
                <p className="text-gray-600 text-xs mt-1">
                  Select a trained model and a test dataset to measure performance.
                </p>
              </div>
              <Button size="sm" icon={<FlaskConical size={13} />} onClick={() => setShowForm(true)}>
                Run first evaluation
              </Button>
            </Card>
          ) : (
            <div className="space-y-3">
              {evaluations.map((ev) => (
                <EvaluationCard key={ev.id} ev={ev} models={models} datasets={datasets} />
              ))}
            </div>
          )}
        </div>
      </AppLayout>
    </>
  );
}