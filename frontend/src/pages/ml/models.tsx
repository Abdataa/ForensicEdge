/**
 * src/pages/ml/models.tsx
 * ────────────────────────
 * AI Engineer — Model Version Management
 *
 * Features
 * ─────────
 *   • List all trained model versions with accuracy ring + metrics
 *   • Activate a model version for live inference (exclusive per evidence type)
 *   • View full metrics JSON (val_loss, precision, recall, F1, etc.)
 *   • Filter by evidence_type
 *   • Active model clearly highlighted per evidence type
 *
 * API
 * ───
 *   GET  /ml/models              mlService.listModels()
 *   GET  /ml/models/:id          mlService.getModel()
 *   POST /ml/models/:id/activate mlService.activateModel()
 */

import { useState, useEffect, useCallback } from "react";
import Head from "next/head";
import {
  Layers, CheckCircle, RefreshCw, Zap, BarChart2,
  TrendingUp, Info, ChevronDown, ChevronUp, Shield,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx  from "clsx";

import AppLayout from "../../components/layout/AppLayout";
import Card      from "../../components/ui/Card";
import Button    from "../../components/ui/Button";
import Spinner   from "../../components/ui/Spinner";
import { mlService, MlModelVersion } from "../../services/mlService";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function AccuracyRing({ value, size = 64 }: { value: number; size?: number }) {
  const r    = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const pct  = Math.min(100, Math.max(0, value));
  const dash = (pct / 100) * circ;
  const color = pct >= 90 ? "#4ade80" : pct >= 75 ? "#facc15" : "#f87171";
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1f2937" strokeWidth={6} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-bold text-white">{pct.toFixed(1)}%</span>
      </div>
    </div>
  );
}

function MetricPill({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="bg-gray-800 rounded-xl px-3 py-2 text-center">
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className={clsx("text-sm font-semibold font-mono", good ? "text-green-400" : "text-yellow-400")}>
        {value}
      </p>
    </div>
  );
}

function fmt(n: number | null | undefined, d = 2) {
  if (n == null) return "—";
  return n.toFixed(d);
}

function relTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Model card
// ─────────────────────────────────────────────────────────────────────────────

function ModelCard({
  model,
  activatingId,
  onActivate,
}: {
  model:        MlModelVersion;
  activatingId: number | null;
  onActivate:   (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const metrics = model.metrics ?? {};

  return (
    <div className={clsx(
      "border rounded-2xl overflow-hidden transition-all",
      model.is_active
        ? "border-green-800 bg-green-950/10"
        : "border-gray-800 bg-gray-900"
    )}>
      {/* Active banner */}
      {model.is_active && (
        <div className="bg-green-950 border-b border-green-800 px-4 py-1.5 flex items-center gap-1.5">
          <Shield size={11} className="text-green-400" />
          <span className="text-xs text-green-400 font-medium">
            Active inference model — {model.evidence_type}
          </span>
        </div>
      )}

      <div className="px-5 py-4">
        <div className="flex items-start gap-4">
          {/* Accuracy ring */}
          <AccuracyRing value={model.accuracy} size={64} />

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-white font-semibold font-mono text-base">
                {model.version}
              </span>
              <span className={clsx(
                "text-xs px-2 py-0.5 rounded-full font-medium",
                model.evidence_type === "fingerprint"
                  ? "bg-purple-950 text-purple-400"
                  : "bg-cyan-950 text-cyan-400"
              )}>
                {model.evidence_type}
              </span>
              {model.is_active && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-950 text-green-400 font-medium flex items-center gap-1">
                  <CheckCircle size={10} /> active
                </span>
              )}
            </div>

            <p className="text-xs text-gray-500 mt-0.5">
              {relTime(model.created_at)}
              {model.training_job_id && ` · Job #${model.training_job_id}`}
            </p>

            {model.notes && (
              <p className="text-xs text-gray-500 mt-1 italic">{model.notes}</p>
            )}

            {/* Quick metric pills */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
              <MetricPill label="Accuracy"   value={`${fmt(model.accuracy, 2)}%`}  good={model.accuracy >= 90} />
              <MetricPill label="Val loss"   value={fmt(model.val_loss, 4)}        good={model.val_loss < 0.2} />
              <MetricPill label="Precision"  value={metrics.precision != null ? `${fmt(metrics.precision as number, 2)}%` : "—"} good={(metrics.precision as number ?? 0) >= 85} />
              <MetricPill label="Recall"     value={metrics.recall != null ? `${fmt(metrics.recall as number, 2)}%` : "—"}     good={(metrics.recall as number ?? 0) >= 85}    />
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2 shrink-0">
            {!model.is_active && (
              <Button
                size="sm"
                icon={activatingId === model.id ? undefined : <Zap size={13} />}
                loading={activatingId === model.id}
                onClick={() => onActivate(model.id)}
              >
                Activate
              </Button>
            )}
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-white transition-colors"
            >
              <Info size={12} />
              {expanded ? "Less" : "Details"}
              {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
          </div>
        </div>

        {/* Expanded metrics */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-800 space-y-3">
            {/* F1 + additional metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { label: "F1 Score",    key: "f1_score"   },
                { label: "FMR",         key: "fmr"        },   // False Match Rate
                { label: "FNMR",        key: "fnmr"       },   // False Non-Match Rate
                { label: "EER",         key: "eer"        },   // Equal Error Rate
              ].map((m) => (
                <MetricPill
                  key={m.label}
                  label={m.label}
                  value={metrics[m.key] != null ? fmt(metrics[m.key] as number, 4) : "—"}
                  good={(metrics[m.key] as number ?? 1) < 0.1}
                />
              ))}
            </div>

            {/* Full metrics JSON */}
            {Object.keys(metrics).length > 0 && (
              <div>
                <p className="text-xs text-gray-600 mb-1.5">Full metrics</p>
                <div className="bg-gray-800 rounded-xl p-3 overflow-x-auto">
                  <pre className="text-xs text-gray-400 whitespace-pre-wrap">
                    {JSON.stringify(metrics, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function ModelsPage() {
  const [models,       setModels]      = useState<MlModelVersion[]>([]);
  const [total,        setTotal]       = useState(0);
  const [loading,      setLoading]     = useState(true);
  const [activatingId, setActivatingId] = useState<number | null>(null);
  const [etFilter,     setEtFilter]    = useState("");

  const loadModels = useCallback(async () => {
    try {
      const res = await mlService.listModels({
        limit: 50,
        ...(etFilter && { evidence_type: etFilter }),
      });
      setModels(res.versions);
      setTotal(res.total);
    } catch {
      toast.error("Could not load model versions.");
    } finally {
      setLoading(false);
    }
  }, [etFilter]);

  useEffect(() => { loadModels(); }, [loadModels]);

  const handleActivate = async (modelId: number) => {
    const model = models.find((m) => m.id === modelId);
    if (!confirm(
      `Activate ${model?.version} as the live inference model for ${model?.evidence_type}?\n\n` +
      `This will immediately replace the current active model.`
    )) return;

    setActivatingId(modelId);
    try {
      await mlService.activateModel(modelId);
      toast.success("Model activated for live inference.");
      await loadModels();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Activation failed.";
      toast.error(detail);
    } finally {
      setActivatingId(null);
    }
  };

  // Split by evidence type for section grouping
  const fpModels = models.filter((m) => m.evidence_type === "fingerprint");
  const tmModels = models.filter((m) => m.evidence_type === "toolmark");

  const activeFingerprint = fpModels.find((m) => m.is_active);
  const activeToolmark    = tmModels.find((m) => m.is_active);

  return (
    <>
      <Head><title>Model Versions — ForensicEdge ML</title></Head>
      <AppLayout title="Model Versions" requiredRole="ai_engineer">
        <div className="space-y-6">

          {/* Header */}
          <div className="flex items-end justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-white font-semibold text-lg">Trained Model Versions</h2>
              <p className="text-gray-500 text-sm mt-0.5">
                {loading ? "Loading…" : `${total} version${total !== 1 ? "s" : ""}`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={etFilter}
                onChange={(e) => setEtFilter(e.target.value)}
                className="field text-sm"
                aria-label="Filter by evidence type"
                style={{ minWidth: 160 }}
              >
                <option value="">All types</option>
                <option value="fingerprint">Fingerprint</option>
                <option value="toolmark">Toolmark</option>
              </select>
              <Button
                size="sm" variant="secondary"
                icon={<RefreshCw size={13} className={loading ? "animate-spin" : ""} />}
                onClick={loadModels} disabled={loading}
              >
                Refresh
              </Button>
            </div>
          </div>

          {/* Active model summary strip */}
          {!loading && (fpModels.length > 0 || tmModels.length > 0) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { label: "Fingerprint — active model", model: activeFingerprint, type: "fingerprint" },
                { label: "Toolmark — active model",    model: activeToolmark,    type: "toolmark"    },
              ].map((s) => (
                <div key={s.type} className={clsx(
                  "flex items-center gap-3 rounded-xl px-4 py-3 border",
                  s.model
                    ? "bg-green-950/20 border-green-900"
                    : "bg-gray-900 border-gray-800"
                )}>
                  <Shield size={16} className={s.model ? "text-green-400" : "text-gray-600"} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-500">{s.label}</p>
                    {s.model ? (
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-white text-sm font-mono font-medium">
                          {s.model.version}
                        </span>
                        <span className="text-xs text-green-400">
                          {s.model.accuracy.toFixed(1)}% accuracy
                        </span>
                      </div>
                    ) : (
                      <p className="text-gray-600 text-sm mt-0.5">No active model</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Model list */}
          {loading ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : models.length === 0 ? (
            <Card className="text-center py-16 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
                <Layers size={28} className="text-gray-600" />
              </div>
              <div>
                <p className="text-gray-400 text-sm font-medium">No trained models yet</p>
                <p className="text-gray-600 text-xs mt-1">
                  Complete a training job to produce a model version.
                </p>
              </div>
            </Card>
          ) : (
            <div className="space-y-6">
              {/* Fingerprint section */}
              {(etFilter === "" || etFilter === "fingerprint") && fpModels.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                      Fingerprint models
                    </h3>
                    <span className="text-xs text-gray-700">({fpModels.length})</span>
                  </div>
                  {fpModels.map((m) => (
                    <ModelCard key={m.id} model={m} activatingId={activatingId} onActivate={handleActivate} />
                  ))}
                </div>
              )}

              {/* Toolmark section */}
              {(etFilter === "" || etFilter === "toolmark") && tmModels.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                      Toolmark models
                    </h3>
                    <span className="text-xs text-gray-700">({tmModels.length})</span>
                  </div>
                  {tmModels.map((m) => (
                    <ModelCard key={m.id} model={m} activatingId={activatingId} onActivate={handleActivate} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </AppLayout>
    </>
  );
}