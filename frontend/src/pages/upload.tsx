/**
 * src/pages/upload.tsx
 * ──────────────────────
 * Evidence image upload page.
 *
 * What changed vs the previous version
 * ──────────────────────────────────────
 *   • Image list now shows ALL images (not just last 10)
 *     via GET /images?evidence_type=&page=&limit=
 *   • Evidence-type filter on the recent-uploads table
 *   • Full pagination on the image list
 *   • Status filter (all / ready / failed / etc.)
 *   • Original side-by-side comparison modal (unchanged)
 *   • Delete (unchanged)
 */

import { useState, useEffect, useCallback } from "react";
import Head   from "next/head";
import { Trash2, Upload as UploadIcon, Eye, RefreshCw } from "lucide-react";
import toast  from "react-hot-toast";
import clsx   from "clsx";

import AppLayout            from "../components/layout/AppLayout";
import Card                 from "../components/ui/Card";
import Button               from "../components/ui/Button";
import { EvidenceBadge, StatusBadge } from "../components/ui/Badge";
import Spinner              from "../components/ui/Spinner";
import Modal                from "../components/ui/modal";
import EvidenceTypeSelector from "../components/forensic/EvidenceTypeSelector";
import ImageUploader        from "../components/forensic/ImageUploader";
import ImageComparison      from "../components/forensic/ImageComparison";

import {
  imageService,
  ImageResponse,
  EvidenceType,
  ImageStatus,
  ComparisonResponse,
} from "../services/imageService";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const LIST_LIMIT = 15;

const ALL_STATUSES: { value: ImageStatus | ""; label: string }[] = [
  { value: "",              label: "All statuses"  },
  { value: "ready",         label: "Ready"         },
  { value: "preprocessed",  label: "Preprocessed"  },
  { value: "preprocessing", label: "Preprocessing" },
  { value: "extracting",    label: "Extracting"    },
  { value: "failed",        label: "Failed"        },
];

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default function UploadPage() {
  // ── Upload section state ──────────────────────────────────────────────────
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("fingerprint");

  // ── Image list state ──────────────────────────────────────────────────────
  const [images,       setImages]       = useState<ImageResponse[]>([]);
  const [total,        setTotal]        = useState(0);
  const [page,         setPage]         = useState(1);
  const [loadingList,  setLoadingList]  = useState(true);
  const [deletingId,   setDeletingId]   = useState<number | null>(null);

  // Filters
  const [filterType,   setFilterType]   = useState<EvidenceType | "">("");
  const [filterStatus, setFilterStatus] = useState<ImageStatus | "">("");

  // ── Comparison modal state ────────────────────────────────────────────────
  const [comparisonOpen,  setComparisonOpen]  = useState(false);
  const [comparisonData,  setComparisonData]  = useState<ComparisonResponse | null>(null);
  const [comparisonLoad,  setComparisonLoad]  = useState(false);
  const [comparisonTitle, setComparisonTitle] = useState("");

  const pages = Math.max(1, Math.ceil(total / LIST_LIMIT));

  // ── Fetch image list ──────────────────────────────────────────────────────
  const loadImages = useCallback(async (
    pg:  number,
    et:  EvidenceType | "",
    st:  ImageStatus  | "",
  ) => {
    setLoadingList(true);
    try {
      const res = await imageService.list({
        page:          pg,
        limit:         LIST_LIMIT,
        evidence_type: et  || undefined,
      });

      // Status is not a backend filter param — filter client-side
      const filtered = st
        ? res.images.filter((i) => i.status === st)
        : res.images;

      setImages(filtered);
      setTotal(st ? filtered.length : res.total);
    } catch {
      toast.error("Could not load images.");
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    loadImages(page, filterType, filterStatus);
  }, [page, filterType, filterStatus, loadImages]);

  // When a filter changes, reset to page 1
  const handleFilterType = (v: EvidenceType | "") => {
    setFilterType(v);
    setPage(1);
  };
  const handleFilterStatus = (v: ImageStatus | "") => {
    setFilterStatus(v);
    setPage(1);
  };

  // ── Upload callback ───────────────────────────────────────────────────────
  const handleUploadComplete = (image: ImageResponse) => {
    // Prepend to list; re-fetch to keep counts accurate
    loadImages(1, filterType, filterStatus);
    setPage(1);
  };

  // ── Delete ────────────────────────────────────────────────────────────────
  const handleDelete = async (image: ImageResponse) => {
    if (!confirm(`Delete "${image.original_filename}"? This cannot be undone.`)) return;
    setDeletingId(image.id);
    try {
      await imageService.delete(image.id);
      setImages((prev) => prev.filter((i) => i.id !== image.id));
      setTotal((t) => t - 1);
      toast.success("Image deleted.");
    } catch {
      toast.error("Delete failed. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  // ── Comparison modal ──────────────────────────────────────────────────────
  const handleViewComparison = async (image: ImageResponse) => {
    setComparisonTitle(image.original_filename);
    setComparisonData(null);
    setComparisonOpen(true);
    setComparisonLoad(true);
    try {
      const result = await imageService.getComparison(image.id);
      setComparisonData(result);
    } catch {
      toast.error("Could not load image comparison.");
      setComparisonOpen(false);
    } finally {
      setComparisonLoad(false);
    }
  };

  const canCompare = (img: ImageResponse) => img.status !== "uploaded";

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <>
      <Head><title>Upload Evidence — ForensicEdge</title></Head>

      <AppLayout title="Upload Evidence">

        {/* ── Evidence type selector ── */}
        <Card>
          <EvidenceTypeSelector
            value={evidenceType}
            onChange={setEvidenceType}
          />
        </Card>

        {/* ── Uploader ── */}
        <Card title="Upload Image">
          <ImageUploader
            evidenceType={evidenceType}
            label={`Upload ${evidenceType} evidence image`}
            onComplete={handleUploadComplete}
          />
          <p className="text-gray-600 text-xs mt-3 leading-relaxed">
            Accepted: BMP, PNG, JPG · Max 10 MB ·
            Image is enhanced (bilateral filter + CLAHE + ridge sharpening) automatically after upload.
          </p>
        </Card>

        {/* ── Image list with filter + pagination ── */}
        <Card title="Uploaded Images" padding="p-0">

          {/* Filter bar */}
          <div className="flex flex-wrap items-end gap-3 px-4 pt-4 pb-3 border-b border-gray-800">
            {/* Evidence type filter */}
            <div className="space-y-1.5">
              <label className="field-label">Evidence type</label>
              <select
                aria-label="Evidence type filter"
                value={filterType}
                onChange={(e) => handleFilterType(e.target.value as EvidenceType | "")}
                className="field"
              >
                <option value="">All types</option>
                <option value="fingerprint">Fingerprint</option>
                <option value="toolmark">Toolmark</option>
              </select>
            </div>

            {/* Status filter */}
            <div className="space-y-1.5">
              <label className="field-label">Status</label>
              <select
                aria-label="Status filter"
                value={filterStatus}
                onChange={(e) => handleFilterStatus(e.target.value as ImageStatus | "")}
                className="field"
              >
                {ALL_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>

            {/* Refresh + count */}
            <div className="ml-auto flex items-center gap-3 self-end">
              <span className="text-xs text-gray-600">
                {loadingList ? "Loading…" : `${total} image${total !== 1 ? "s" : ""}`}
              </span>
              <button
                onClick={() => loadImages(page, filterType, filterStatus)}
                disabled={loadingList}
                className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-gray-800 transition-colors disabled:opacity-40"
                title="Refresh"
              >
                <RefreshCw size={14} className={loadingList ? "animate-spin" : ""} />
              </button>
            </div>
          </div>

          {/* Table body */}
          {loadingList ? (
            <div className="flex justify-center py-10">
              <Spinner size="md" />
            </div>

          ) : images.length === 0 ? (
            <div className="text-center py-12 space-y-3 px-6">
              <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
                <UploadIcon size={24} className="text-gray-600" />
              </div>
              <p className="text-gray-500 text-sm">
                {filterType || filterStatus ? "No images match your filters." : "No images uploaded yet."}
              </p>
              {!(filterType || filterStatus) && (
                <p className="text-gray-600 text-xs">Upload an image above to get started.</p>
              )}
            </div>

          ) : (
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Uploaded</th>
                    <th>Compare</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {images.map((img) => (
                    <tr key={img.id}>

                      {/* Filename */}
                      <td>
                        <span
                          className="block truncate max-w-[180px] text-white text-sm"
                          title={img.original_filename}
                        >
                          {img.original_filename}
                        </span>
                        <span className="text-gray-600 text-xs">ID: {img.id}</span>
                      </td>

                      <td><EvidenceBadge type={img.evidence_type} /></td>

                      <td className="text-gray-400 whitespace-nowrap text-xs">
                        {(img.file_size_bytes / 1024).toFixed(1)} KB
                      </td>

                      <td><StatusBadge status={img.status} /></td>

                      <td className="text-gray-500 text-xs whitespace-nowrap">
                        {new Date(img.upload_date).toLocaleString(undefined, {
                          month: "short", day: "numeric",
                          hour: "2-digit", minute: "2-digit",
                        })}
                      </td>

                      {/* View original vs enhanced */}
                      <td>
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={<Eye size={13} />}
                          disabled={!canCompare(img)}
                          onClick={() => handleViewComparison(img)}
                          className="whitespace-nowrap"
                        >
                          View
                        </Button>
                      </td>

                      {/* Delete */}
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={
                            deletingId === img.id
                              ? <Spinner size="sm" />
                              : <Trash2 size={14} />
                          }
                          disabled={deletingId === img.id}
                          onClick={() => handleDelete(img)}
                          aria-label={`Delete ${img.original_filename}`}
                          className="text-gray-600 hover:text-red-400"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination footer */}
          {pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
              <span className="text-xs text-gray-500">
                Page {page} of {pages}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 rounded-lg text-xs border border-gray-800
                             text-gray-500 hover:text-white hover:border-gray-600
                             disabled:opacity-40 disabled:pointer-events-none transition-colors"
                >
                  ← Prev
                </button>
                {Array.from({ length: Math.min(pages, 7) }, (_, i) => {
                  const lo = Math.max(1, page - 3);
                  return lo + i;
                })
                  .filter((p) => p <= pages)
                  .map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={clsx(
                        "px-3 py-1.5 rounded-lg text-xs border transition-colors",
                        p === page
                          ? "border-gray-600 bg-gray-800 text-white font-medium"
                          : "border-gray-800 text-gray-500 hover:text-white hover:border-gray-600"
                      )}
                    >
                      {p}
                    </button>
                  ))}
                <button
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  disabled={page === pages}
                  className="px-3 py-1.5 rounded-lg text-xs border border-gray-800
                             text-gray-500 hover:text-white hover:border-gray-600
                             disabled:opacity-40 disabled:pointer-events-none transition-colors"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </Card>

      </AppLayout>

      {/* ── Original vs Enhanced modal ── */}
      <Modal
        open={comparisonOpen}
        onClose={() => setComparisonOpen(false)}
        title={`Original vs Enhanced — ${comparisonTitle}`}
        maxWidth="max-w-3xl"
      >
        {comparisonLoad ? (
          <div className="flex items-center justify-center gap-3 py-16">
            <Spinner size="md" />
            <p className="text-gray-400 text-sm">Loading image data…</p>
          </div>
        ) : comparisonData ? (
          <ImageComparison data={comparisonData} modal />
        ) : null}
      </Modal>
    </>
  );
}