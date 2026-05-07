/**
 * src/pages/ml/datasets.tsx
 * ──────────────────────────
 * AI Engineer — Dataset Management
 *
 * Features
 * ─────────
 *   • List all datasets with status, image count, size, evidence type
 *   • Upload new dataset as zip archive (multipart/form-data)
 *   • Live upload progress bar
 *   • Delete dataset with confirmation
 *   • Filter by evidence_type and status
 *   • Auto-refresh "processing" datasets every 5 s
 *
 * API
 * ───
 *   GET    /ml/datasets          mlService.listDatasets()
 *   POST   /ml/datasets          mlService.uploadDataset()
 *   DELETE /ml/datasets/:id      mlService.deleteDataset()
 */

import { useState, useEffect, useRef, useCallback, FormEvent } from "react";
import Head          from "next/head";
import {
  Database, Upload, Trash2, RefreshCw, Plus, ChevronUp,
  CheckCircle, XCircle, Clock, AlertTriangle, FileArchive,
  Image as ImageIcon, HardDrive, Filter,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx  from "clsx";

import AppLayout from "../../components/layout/AppLayout";
import Card      from "../../components/ui/Card";
import Button    from "../../components/ui/Button";
import Input     from "../../components/ui/Input";
import Spinner   from "../../components/ui/Spinner";
import { mlService, MlDataset } from "../../services/mlService";

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

const STATUS_CFG = {
  ready:      { icon: <CheckCircle size={12} />, cls: "bg-green-950  text-green-400",  label: "Ready"      },
  processing: { icon: <RefreshCw   size={12} className="animate-spin" />, cls: "bg-blue-950   text-blue-400",   label: "Processing" },
  error:      { icon: <XCircle     size={12} />, cls: "bg-red-950    text-red-400",    label: "Error"      },
} as const;

function DatasetStatusBadge({ status }: { status: MlDataset["status"] }) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.error;
  return (
    <span className={clsx("inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium", cfg.cls)}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

function EvidenceTypePill({ type }: { type: string }) {
  const cls = type === "fingerprint"
    ? "bg-purple-950 text-purple-400"
    : "bg-cyan-950 text-cyan-400";
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", cls)}>
      {type}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Upload form
// ─────────────────────────────────────────────────────────────────────────────

interface UploadFormProps {
  onSuccess: () => void;
  onCancel:  () => void;
}

function UploadForm({ onSuccess, onCancel }: UploadFormProps) {
  const [name,          setName]          = useState("");
  const [evidenceType,  setEvidenceType]  = useState<"fingerprint" | "toolmark">("fingerprint");
  const [description,   setDescription]   = useState("");
  const [file,          setFile]          = useState<File | null>(null);
  const [uploading,     setUploading]     = useState(false);
  const [uploadPct,     setUploadPct]     = useState(0);
  const [error,         setError]         = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.endsWith(".zip")) {
      setError("Only .zip archives are accepted.");
      return;
    }
    setError("");
    setFile(f);
    if (!name) setName(f.name.replace(/\.zip$/i, ""));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) { setError("Please select a zip archive."); return; }
    setError("");
    setUploading(true);
    setUploadPct(0);

    // Simulate upload progress (real XHR progress would use axios onUploadProgress)
    const ticker = setInterval(() => setUploadPct((p) => Math.min(p + 8, 90)), 200);

    try {
      const formData = new FormData();
      formData.append("name",          name.trim());
      formData.append("evidence_type", evidenceType);
      formData.append("description",   description.trim());
      formData.append("file",          file);

      await mlService.uploadDataset(formData);
      clearInterval(ticker);
      setUploadPct(100);
      toast.success("Dataset upload started — processing in background.");
      setTimeout(onSuccess, 600);
    } catch (err: unknown) {
      clearInterval(ticker);
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Upload failed.";
      setError(detail);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card title="Upload new dataset">
      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm mb-4">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Dataset name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="FVC2000-DB1-fingerprint"
            required
            minLength={2}
            disabled={uploading}
          />
          <div className="space-y-1.5">
            <label htmlFor="dataset-evidence-type" className="field-label">Evidence type</label>
            <select
              id="dataset-evidence-type"
              value={evidenceType}
              onChange={(e) => setEvidenceType(e.target.value as "fingerprint" | "toolmark")}
              disabled={uploading}
              className="field"
            >
              <option value="fingerprint">Fingerprint</option>
              <option value="toolmark">Toolmark</option>
            </select>
          </div>
        </div>

        <Input
          label="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="FVC2000 DB1-A — 800 images, 100 fingers × 8 impressions"
          disabled={uploading}
        />

        {/* File drop zone */}
        <div
          onClick={() => !uploading && fileRef.current?.click()}
          className={clsx(
            "border-2 border-dashed rounded-2xl px-6 py-8 text-center transition-colors cursor-pointer",
            file
              ? "border-green-700 bg-green-950/30"
              : "border-gray-700 hover:border-gray-500 bg-gray-900/50",
            uploading && "pointer-events-none opacity-60"
          )}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={handleFileChange}
            disabled={uploading}
            title="Select a .zip archive"
          />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileArchive size={24} className="text-green-400 shrink-0" />
              <div className="text-left">
                <p className="text-white text-sm font-medium">{file.name}</p>
                <p className="text-gray-500 text-xs">
                  {(file.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <FileArchive size={28} className="text-gray-600 mx-auto" />
              <p className="text-gray-400 text-sm font-medium">
                Click to select a .zip archive
              </p>
              <p className="text-gray-600 text-xs">
                Must contain labelled image files (jpg, png, bmp, tiff)
              </p>
            </div>
          )}
        </div>

        {/* Upload progress */}
        {uploading && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Uploading…</span>
              <span>{uploadPct}%</span>
            </div>
            <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-300"
                style={{ width: `${uploadPct}%` }}
              />
            </div>
          </div>
        )}

        {/* Validation rules */}
        <div className="bg-gray-900 rounded-xl px-4 py-3 space-y-1.5 text-xs text-gray-500">
          <p className="text-gray-400 font-medium mb-1">Dataset requirements</p>
          <p className="flex items-center gap-1.5"><CheckCircle size={11} className="text-green-500" /> Zip archive containing image files</p>
          <p className="flex items-center gap-1.5"><CheckCircle size={11} className="text-green-500" /> Accepted formats: jpg, jpeg, png, bmp, tiff</p>
          <p className="flex items-center gap-1.5"><CheckCircle size={11} className="text-green-500" /> Sub-directories allowed (class folders)</p>
          <p className="flex items-center gap-1.5"><AlertTriangle size={11} className="text-yellow-500" /> Minimum 50 images recommended for training</p>
        </div>

        <div className="flex items-center gap-3">
          <Button type="submit" loading={uploading} icon={<Upload size={14} />}>
            {uploading ? "Uploading…" : "Upload dataset"}
          </Button>
          <Button type="button" variant="secondary" onClick={onCancel} disabled={uploading}>
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

export default function DatasetsPage() {
  const [datasets,      setDatasets]      = useState<MlDataset[]>([]);
  const [total,         setTotal]         = useState(0);
  const [loading,       setLoading]       = useState(true);
  const [showForm,      setShowForm]      = useState(false);
  const [deletingId,    setDeletingId]    = useState<number | null>(null);
  const [etFilter,      setEtFilter]      = useState("");
  const [statusFilter,  setStatusFilter]  = useState("");

  const hasProcessing = datasets.some((d) => d.status === "processing");

  const loadDatasets = useCallback(async () => {
    try {
      const res = await mlService.listDatasets({
        limit: 100,
        ...(etFilter     && { evidence_type: etFilter }),
        ...(statusFilter && { status: statusFilter }),
      });
      setDatasets(res.datasets);
      setTotal(res.total);
    } catch {
      toast.error("Could not load datasets.");
    } finally {
      setLoading(false);
    }
  }, [etFilter, statusFilter]);

  useEffect(() => { loadDatasets(); }, [loadDatasets]);

  // Auto-refresh while any dataset is still processing
  useEffect(() => {
    if (!hasProcessing) return;
    const id = setInterval(loadDatasets, 5000);
    return () => clearInterval(id);
  }, [hasProcessing, loadDatasets]);

  const handleDelete = async (ds: MlDataset) => {
    if (!confirm(`Delete dataset "${ds.name}"?\n\nThis removes the files from disk. Training jobs that used it are preserved.`)) return;
    setDeletingId(ds.id);
    try {
      await mlService.deleteDataset(ds.id);
      toast.success("Dataset deleted.");
      setDatasets((prev) => prev.filter((d) => d.id !== ds.id));
      setTotal((t) => t - 1);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Delete failed.";
      toast.error(detail);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <Head><title>Datasets — ForensicEdge ML</title></Head>
      <AppLayout title="Dataset Management" requiredRole="ai_engineer">
        <div className="space-y-5">

          {/* Header */}
          <div className="flex items-end justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-white font-semibold text-lg">Training Datasets</h2>
              <p className="text-gray-500 text-sm mt-0.5">
                {loading ? "Loading…" : `${total} dataset${total !== 1 ? "s" : ""}`}
                {hasProcessing && (
                  <span className="ml-2 text-blue-400 inline-flex items-center gap-1">
                    <RefreshCw size={11} className="animate-spin" /> processing…
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                icon={<RefreshCw size={13} className={loading ? "animate-spin" : ""} />}
                onClick={loadDatasets}
                disabled={loading}
              >
                Refresh
              </Button>
              <Button
                size="sm"
                icon={showForm ? <ChevronUp size={14} /> : <Plus size={14} />}
                onClick={() => setShowForm((v) => !v)}
              >
                {showForm ? "Cancel" : "Upload dataset"}
              </Button>
            </div>
          </div>

          {/* Upload form */}
          {showForm && (
            <UploadForm
              onSuccess={() => { setShowForm(false); loadDatasets(); }}
              onCancel={() => setShowForm(false)}
            />
          )}

          {/* Filters */}
          <Card>
            <div className="flex items-center gap-2 flex-wrap">
              <Filter size={14} className="text-gray-500 shrink-0" />
              <div className="flex gap-3 flex-wrap flex-1">
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
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="field text-sm"
                  aria-label="Filter by status"
                  style={{ minWidth: 160 }}
                >
                  <option value="">All statuses</option>
                  <option value="ready">Ready</option>
                  <option value="processing">Processing</option>
                  <option value="error">Error</option>
                </select>
                {(etFilter || statusFilter) && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => { setEtFilter(""); setStatusFilter(""); }}
                  >
                    Clear
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {/* Table */}
          {loading ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : datasets.length === 0 ? (
            <Card className="text-center py-16 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
                <Database size={28} className="text-gray-600" />
              </div>
              <div>
                <p className="text-gray-400 text-sm font-medium">No datasets yet</p>
                <p className="text-gray-600 text-xs mt-1">
                  Upload a zip archive of labelled forensic images to get started.
                </p>
              </div>
              <Button size="sm" icon={<Upload size={13} />} onClick={() => setShowForm(true)}>
                Upload first dataset
              </Button>
            </Card>
          ) : (
            <Card padding="p-0">
              <div className="overflow-x-auto">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Images</th>
                      <th>Size</th>
                      <th>Status</th>
                      <th>Uploaded</th>
                      <th className="w-16">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datasets.map((ds) => (
                      <tr key={ds.id}>
                        <td>
                          <div>
                            <p className="text-white font-medium">{ds.name}</p>
                            {ds.description && (
                              <p className="text-gray-600 text-xs mt-0.5 truncate max-w-xs">
                                {ds.description}
                              </p>
                            )}
                            {ds.status === "error" && ds.error_message && (
                              <p className="text-red-500 text-xs mt-0.5 truncate max-w-xs">
                                {ds.error_message}
                              </p>
                            )}
                          </div>
                        </td>
                        <td><EvidenceTypePill type={ds.evidence_type} /></td>
                        <td>
                          <span className="flex items-center gap-1 text-gray-300 font-mono text-sm">
                            <ImageIcon size={12} className="text-gray-600" />
                            {ds.image_count > 0 ? ds.image_count.toLocaleString() : "—"}
                          </span>
                        </td>
                        <td>
                          <span className="flex items-center gap-1 text-gray-400 text-sm">
                            <HardDrive size={12} className="text-gray-600" />
                            {ds.size_mb > 0 ? `${ds.size_mb.toFixed(1)} MB` : "—"}
                          </span>
                        </td>
                        <td><DatasetStatusBadge status={ds.status} /></td>
                        <td className="text-gray-500 text-xs whitespace-nowrap">
                          {new Date(ds.created_at).toLocaleDateString(undefined, {
                            month: "short", day: "numeric", year: "numeric",
                          })}
                        </td>
                        <td>
                          <button
                            onClick={() => handleDelete(ds)}
                            disabled={deletingId === ds.id || ds.status === "processing"}
                            title="Delete dataset"
                            className="p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-gray-800 transition-colors disabled:opacity-40"
                          >
                            {deletingId === ds.id ? <Spinner size="sm" /> : <Trash2 size={14} />}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Stats summary */}
          {datasets.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                {
                  label: "Total images",
                  value: datasets.reduce((a, d) => a + d.image_count, 0).toLocaleString(),
                  icon:  <ImageIcon size={15} className="text-blue-400" />,
                },
                {
                  label: "Total size",
                  value: `${datasets.reduce((a, d) => a + d.size_mb, 0).toFixed(1)} MB`,
                  icon:  <HardDrive size={15} className="text-purple-400" />,
                },
                {
                  label: "Fingerprint sets",
                  value: datasets.filter((d) => d.evidence_type === "fingerprint").length,
                  icon:  <Database size={15} className="text-cyan-400" />,
                },
                {
                  label: "Toolmark sets",
                  value: datasets.filter((d) => d.evidence_type === "toolmark").length,
                  icon:  <Database size={15} className="text-green-400" />,
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
        </div>
      </AppLayout>
    </>
  );
}