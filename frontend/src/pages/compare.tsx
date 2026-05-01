/**
 * src/pages/compare.tsx
 * ──────────────────────
 * Forensic evidence comparison — three tabs in one page:
 *
 *   Tab 1 · Compare Evidence   (original workflow, fully preserved)
 *   ────────────────────────────────────────────────────────────────
 *   1. Select evidence type (fingerprint | toolmark)
 *   2. Upload query image   → left  ImageUploader
 *   3. Upload reference image → right ImageUploader
 *   4. Both reach status="ready" → Compare button activates
 *   5. POST /compare → SimilarityResultCard renders result
 *   6. Generate PDF report | submit thumbs feedback
 *
 *   Tab 2 · Database Search    (new)
 *   ────────────────────────────────────────────────────────────────
 *   Pick ONE ready image → POST /compare/search
 *   Returns ranked candidates from the entire database.
 *
 *   Tab 3 · Past Results       (new)
 *   ────────────────────────────────────────────────────────────────
 *   GET /compare?page=&limit=&evidence_type=
 *   Paginated list of all previous two-image comparisons.
 *   Click any row to expand full metrics.
 *
 * Services used
 * ──────────────
 *   compareService  — compare()             (existing, unchanged)
 *   reportService   — generate(), download() (existing, unchanged)
 *   imageService    — list(), searchDatabase(), listResults() (existing)
 */

import { useState, useEffect, useCallback } from "react";
import Head from "next/head";
import {
  GitCompare,
  AlertTriangle,
  Search,
  History,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  Fingerprint,
  Wrench,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx  from "clsx";

import AppLayout            from "../components/layout/AppLayout";
import Card                 from "../components/ui/Card";
import Button               from "../components/ui/Button";
import Spinner              from "../components/ui/Spinner";
import { EvidenceBadge }    from "../components/ui/Badge";
import EvidenceTypeSelector from "../components/forensic/EvidenceTypeSelector";
import ImageUploader        from "../components/forensic/ImageUploader";
import SimilarityResultCard from "../components/forensic/SimilarityResultCard";
import FeedbackForm         from "../components/forensic/FeedbackForm";

import {
  imageService,
  ImageResponse,
  DatabaseSearchResponse,
  SimilarityListResponse,
  EvidenceType,
  MatchStatus,
} from "../services/imageService";
import { compareService, SimilarityResponse, } from "../services/compareService";
import { reportService }                       from "../services/reportService";

// ─────────────────────────────────────────────────────────────────────────────
// Constants & small helpers
// ─────────────────────────────────────────────────────────────────────────────

const RESULTS_PER_PAGE = 15;

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function fmtPct(n: number) {
  return `${n.toFixed(1)}%`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared display sub-components
// ─────────────────────────────────────────────────────────────────────────────

function SimilarityPill({ pct, status }: { pct: number; status: MatchStatus }) {
  const cls =
    status === "MATCH"
      ? "bg-green-950 text-green-400 border border-green-800"
      : status === "POSSIBLE MATCH"
      ? "bg-yellow-950 text-yellow-400 border border-yellow-800"
      : "bg-red-950 text-red-400 border border-red-800";
  return (
    <span className={clsx("text-sm font-semibold px-3 py-1 rounded-full tabular-nums", cls)}>
      {fmtPct(pct)}
    </span>
  );
}

function MatchBadge({ status }: { status: MatchStatus }) {
  const map = {
    "MATCH":          { Icon: CheckCircle2, cls: "text-green-400" },
    "POSSIBLE MATCH": { Icon: HelpCircle,   cls: "text-yellow-400" },
    "NO MATCH":       { Icon: AlertCircle,  cls: "text-red-400"   },
  };
  const { Icon, cls } = map[status];
  return (
    <span className={clsx("inline-flex items-center gap-1 text-xs font-medium", cls)}>
      <Icon size={13} />
      {status}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-600 uppercase tracking-wide">{label}</span>
      <span className="text-sm font-mono text-gray-300">{value}</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 1 — Two-image comparison  (your original workflow, 100% preserved)
// ─────────────────────────────────────────────────────────────────────────────

function ComparePanel() {
  const [evidenceType,      setEvidenceType]      = useState<EvidenceType>("fingerprint");
  const [image1,            setImage1]            = useState<ImageResponse | null>(null);
  const [image2,            setImage2]            = useState<ImageResponse | null>(null);
  const [result,            setResult]            = useState<SimilarityResponse | null>(null);
  const [comparing,         setComparing]         = useState(false);
  const [generating,        setGenerating]        = useState(false);
  const [error,             setError]             = useState("");
  const [feedbackOpen,      setFeedbackOpen]      = useState(false);
  const [feedbackCorrect,   setFeedbackCorrect]   = useState(true);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const canCompare = image1?.status === "ready" && image2?.status === "ready";

  const handleTypeChange = (type: EvidenceType) => {
    setEvidenceType(type);
    setImage1(null);
    setImage2(null);
    setResult(null);
    setError("");
    setFeedbackSubmitted(false);
  };

  const handleCompare = async () => {
    if (!image1 || !image2) return;
    setError("");
    setComparing(true);
    setResult(null);
    setFeedbackSubmitted(false);
    try {
      const res = await compareService.compare(image1.id, image2.id);
      setResult(res);
      toast.success("Analysis complete.");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? "Comparison failed. Please try again.";
      setError(detail);
    } finally {
      setComparing(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!result) return;
    setGenerating(true);
    try {
      const report = await reportService.generate(
        result.id,
        `Analysis Report — Result #${result.id}`,
      );
      await reportService.download(report.id, `forensic_report_${result.id}.pdf`);
      toast.success("Report downloaded.");
    } catch (err: unknown) {
      if ((err as { response?: { status?: number } })?.response?.status === 409) {
        toast.error("A report already exists for this result. Check the Reports page.");
      } else {
        const detail =
          (err as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail ?? "Report generation failed.";
        toast.error(detail);
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleFeedback = (isCorrect: boolean) => {
    setFeedbackCorrect(isCorrect);
    setFeedbackOpen(true);
  };

  return (
    <>
      {/* Evidence type */}
      <Card>
        <EvidenceTypeSelector
          value={evidenceType}
          onChange={handleTypeChange}
          disabled={comparing}
        />
      </Card>

      {/* Two uploaders */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <ImageUploader
            evidenceType={evidenceType}
            label="Query image — evidence to identify"
            onComplete={(img) => { setImage1(img); setResult(null); }}
          />
        </Card>
        <Card>
          <ImageUploader
            evidenceType={evidenceType}
            label="Reference image — known sample"
            onComplete={(img) => { setImage2(img); setResult(null); }}
          />
        </Card>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-2.5 bg-red-950 border border-red-800
                        rounded-xl px-4 py-3 text-red-300 text-sm">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Compare button */}
      <div className="flex flex-col items-center gap-2">
        <Button
          size="lg"
          icon={<GitCompare size={18} />}
          loading={comparing}
          disabled={!canCompare || comparing}
          onClick={handleCompare}
          className="px-10"
        >
          {comparing ? "Analysing…" : "Run Forensic Comparison"}
        </Button>

        {!canCompare && (image1 || image2) && (
          <p className="text-gray-600 text-xs text-center">
            Waiting for both images to finish processing
            (status: <span className="text-green-500">ready</span>)
          </p>
        )}
        {!image1 && !image2 && (
          <p className="text-gray-600 text-xs text-center">
            Upload a query image and a reference image above, then click Compare.
          </p>
        )}
      </div>

      {/* Result card */}
      {result && (
        <div className="max-w-lg mx-auto w-full">
          <SimilarityResultCard
            result={result}
            onGenerateReport={handleGenerateReport}
            onFeedback={feedbackSubmitted ? undefined : handleFeedback}
            isGenerating={generating}
          />
          {feedbackSubmitted && (
            <p className="text-center text-gray-600 text-xs mt-2">
              Feedback submitted — thank you.
            </p>
          )}
        </div>
      )}

      {/* Feedback modal — renders outside the card so it overlays correctly */}
      {feedbackOpen && result && (
        <FeedbackForm
          resultId={result.id}
          isCorrect={feedbackCorrect}
          onClose={() => setFeedbackOpen(false)}
          onSubmitted={() => setFeedbackSubmitted(true)}
        />
      )}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 2 — Database search (single image → ranked candidates)
// ─────────────────────────────────────────────────────────────────────────────

function DatabaseSearchPanel() {
  const [readyImages, setReadyImages] = useState<ImageResponse[]>([]);
  const [loadingImgs, setLoadingImgs] = useState(true);
  const [selectedId,  setSelectedId]  = useState<number | "">("");
  const [topK,        setTopK]        = useState(10);
  const [threshold,   setThreshold]   = useState(0);
  const [searching,   setSearching]   = useState(false);
  const [result,      setResult]      = useState<DatabaseSearchResponse | null>(null);
  const [searched,    setSearched]    = useState(false);

  useEffect(() => {
    imageService
      .list({ limit: 100 })
      .then((res) => setReadyImages(res.images.filter((i) => i.status === "ready")))
      .catch(() => toast.error("Could not load images."))
      .finally(() => setLoadingImgs(false));
  }, []);

  const handleSearch = async () => {
    if (!selectedId) { toast.error("Select a query image first."); return; }
    setSearching(true);
    setResult(null);
    setSearched(false);
    try {
      const res = await imageService.searchDatabase({
        image_id:  Number(selectedId),
        top_k:     topK,
        threshold,
      });
      setResult(res);
      setSearched(true);
    } catch {
      toast.error("Database search failed. Please try again.");
    } finally {
      setSearching(false);
    }
  };

  const selectedImage = readyImages.find((i) => i.id === Number(selectedId));

  return (
    <div className="space-y-5">
      <Card title="Search configuration">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
          {/* Image selector */}
          <div className="sm:col-span-2 space-y-1.5">
            <label className="field-label">Query image</label>
            {loadingImgs ? (
              <div className="flex items-center gap-2 h-10">
                <Spinner size="sm" />
                <span className="text-gray-500 text-sm">Loading images…</span>
              </div>
            ) : readyImages.length === 0 ? (
              <p className="text-yellow-500 text-sm py-2">
                No ready images found. Upload and process an image first.
              </p>
            ) : (
              <select
                value={selectedId}
                onChange={(e) =>
                  setSelectedId(e.target.value === "" ? "" : Number(e.target.value))
                }
                className="field"
              >
                <option value="">— Select an image to search with —</option>
                {readyImages.map((img) => (
                  <option key={img.id} value={img.id}>
                    [{img.id}] {img.original_filename} · {img.evidence_type}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Top K */}
          <div className="space-y-1.5">
            <label className="field-label">
              Top results{" "}
              <span className="text-gray-600 font-normal">(max candidates)</span>
            </label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="field"
            >
              {[5, 10, 20, 50].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Threshold slider */}
        <div className="mt-4 space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="field-label">Minimum similarity threshold</label>
            <span className="text-sm font-semibold text-white tabular-nums">
              {threshold}%
            </span>
          </div>
          <input
            type="range"
            min={0} max={95} step={5}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full h-1.5 bg-gray-800 rounded-full appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-white"
          />
          <div className="flex justify-between text-xs text-gray-700">
            <span>0% (all)</span><span>50%</span><span>95%</span>
          </div>
        </div>

        {/* Selected image info strip */}
        {selectedImage && (
          <div className="mt-4 flex items-center gap-3 bg-gray-900 rounded-xl px-4 py-3">
            <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center shrink-0">
              {selectedImage.evidence_type === "fingerprint"
                ? <Fingerprint size={16} className="text-gray-400" />
                : <Wrench      size={16} className="text-gray-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {selectedImage.original_filename}
              </p>
              <p className="text-xs text-gray-500">
                ID {selectedImage.id} · {selectedImage.evidence_type} ·{" "}
                {(selectedImage.file_size_bytes / 1024).toFixed(1)} KB
              </p>
            </div>
            <EvidenceBadge type={selectedImage.evidence_type} />
          </div>
        )}

        <div className="mt-4">
          <Button
            onClick={handleSearch}
            loading={searching}
            disabled={!selectedId || loadingImgs}
            icon={<Search size={14} />}
          >
            Search database
          </Button>
        </div>
      </Card>

      {/* Searching spinner */}
      {searching && (
        <div className="flex items-center justify-center gap-3 py-10">
          <Spinner size="md" />
          <p className="text-gray-400 text-sm">Scanning database…</p>
        </div>
      )}

      {/* Results */}
      {searched && result && !searching && (
        <>
          <div className="flex items-center gap-4 flex-wrap">
            <h3 className="text-white font-semibold">Search results</h3>
            <span className="text-gray-500 text-sm">
              {result.candidates.length} candidate
              {result.candidates.length !== 1 ? "s" : ""} from{" "}
              {result.total_searched} image
              {result.total_searched !== 1 ? "s" : ""} searched
            </span>
            {result.candidates.length > 0 && (
              <span className="ml-auto text-xs text-gray-600">
                Ordered by similarity (highest first)
              </span>
            )}
          </div>

          {result.candidates.length === 0 ? (
            <Card className="text-center py-12 space-y-3">
              <AlertCircle size={28} className="text-gray-600 mx-auto" />
              <p className="text-gray-400 text-sm font-medium">No matches found</p>
              <p className="text-gray-600 text-xs">
                No images met the {threshold}% threshold. Try lowering it.
              </p>
            </Card>
          ) : (
            <Card padding="p-0">
              <div className="overflow-x-auto">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th className="w-8">#</th>
                      <th>Candidate image</th>
                      <th>Type</th>
                      <th>Similarity</th>
                      <th>Match status</th>
                      <th>Cosine</th>
                      <th>Euclidean</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.candidates.map((c, idx) => (
                      <tr key={c.image.id}>
                        <td className="text-gray-600 text-xs">{idx + 1}</td>
                        <td>
                          <span
                            className="text-white text-sm font-medium block truncate max-w-[200px]"
                            title={c.image.original_filename}
                          >
                            {c.image.original_filename}
                          </span>
                          <span className="text-gray-600 text-xs">ID: {c.image.id}</span>
                        </td>
                        <td><EvidenceBadge type={c.image.evidence_type} /></td>
                        <td>
                          <SimilarityPill
                            pct={c.similarity_percentage}
                            status={c.match_status}
                          />
                        </td>
                        <td><MatchBadge status={c.match_status} /></td>
                        <td className="text-gray-400 text-xs font-mono">
                          {c.cosine_similarity.toFixed(4)}
                        </td>
                        <td className="text-gray-400 text-xs font-mono">
                          {c.euclidean_distance.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab 3 — Past two-image comparison results
// ─────────────────────────────────────────────────────────────────────────────

function PastResultsPanel() {
  const [data,       setData]       = useState<SimilarityListResponse | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState<string | null>(null);
  const [page,       setPage]       = useState(1);
  const [filterType, setFilterType] = useState<EvidenceType | "">("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchResults = useCallback(
    async (pg: number, et: EvidenceType | "") => {
      setLoading(true);
      setError(null);
      try {
        const res = await imageService.listResults({
          page: pg, limit: RESULTS_PER_PAGE,
          evidence_type: et || undefined,
        });
        setData(res);
      } catch {
        setError("Could not load comparison results.");
        toast.error("Failed to load past comparisons.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => { fetchResults(page, filterType); }, [page, filterType, fetchResults]);

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / RESULTS_PER_PAGE));

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="space-y-1.5">
          <label className="field-label">Filter by type</label>
          <select
            value={filterType}
            onChange={(e) => {
              setFilterType(e.target.value as EvidenceType | "");
              setPage(1);
              setExpandedId(null);
            }}
            className="field"
          >
            <option value="">All evidence types</option>
            <option value="fingerprint">Fingerprint</option>
            <option value="toolmark">Toolmark</option>
          </select>
        </div>
        <div className="ml-auto self-end">
          <p className="text-xs text-gray-500">
            {loading ? "Loading…" : `${total} result${total !== 1 ? "s" : ""}`}
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-14"><Spinner size="lg" /></div>
      ) : data?.results.length === 0 ? (
        <Card className="text-center py-12 space-y-3">
          <History size={28} className="text-gray-600 mx-auto" />
          <p className="text-gray-400 text-sm font-medium">No comparison results yet</p>
          <p className="text-gray-600 text-xs">
            Run a comparison on the Compare Evidence tab to see results here.
          </p>
        </Card>
      ) : (
        <Card padding="p-0">
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th className="w-8"></th>
                  <th>Image A</th>
                  <th>Image B</th>
                  <th>Type</th>
                  <th>Similarity</th>
                  <th>Match</th>
                  <th className="whitespace-nowrap">Compared</th>
                </tr>
              </thead>
              <tbody>
                {data?.results.map((r) => (
                  <>
                    <tr
                      key={r.id}
                      className="cursor-pointer"
                      onClick={() =>
                        setExpandedId((prev) => (prev === r.id ? null : r.id))
                      }
                    >
                      <td className="text-gray-600">
                        {expandedId === r.id
                          ? <ChevronUp size={14} />
                          : <ChevronDown size={14} />}
                      </td>
                      <td>
                        <span
                          className="text-white text-sm font-medium block truncate max-w-[160px]"
                          title={r.image_1?.original_filename ?? "Unknown image"}
                        >
                          {r.image_2?.original_filename ?? "Unknown image"}
                        </span>
                        <span className="text-gray-600 text-xs">ID: {r.image_1.id}</span>
                      </td>
                      <td>
                        <span
                          className="text-white text-sm font-medium block truncate max-w-[160px]"
                          title={r.image_1.original_filename}
                        >
                          {r.image_2.original_filename}
                        </span>
                        <span className="text-gray-600 text-xs">ID: {r.image_2.id}</span>
                      </td>
                      <td><EvidenceBadge type={r.evidence_type} /></td>
                      <td>
                        <SimilarityPill
                          pct={r.similarity_percentage}
                          status={r.match_status}
                        />
                      </td>
                      <td><MatchBadge status={r.match_status} /></td>
                      <td className="text-gray-500 text-xs whitespace-nowrap">
                        {fmtDate(r.created_at)}
                      </td>
                    </tr>

                    {expandedId === r.id && (
                      <tr key={`${r.id}-detail`} className="bg-gray-950">
                        <td colSpan={7} className="px-4 py-4">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 pl-2">
                            <Metric label="Similarity %"       value={fmtPct(r.similarity_percentage)} />
                            <Metric label="Cosine similarity"  value={r.cosine_similarity.toFixed(6)} />
                            <Metric label="Euclidean distance" value={r.euclidean_distance.toFixed(6)} />
                            <Metric label="Result ID"          value={`#${r.id}`} />
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">Page {page} of {pages}</span>
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
            {Array.from({ length: Math.min(pages, 7) }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-xs border transition-colors",
                  p === page
                    ? "border-gray-600 bg-gray-800 text-white font-medium"
                    : "border-gray-800 text-gray-500 hover:text-white hover:border-gray-600",
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
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page root — three-tab shell
// ─────────────────────────────────────────────────────────────────────────────

type TabId = "compare" | "search" | "history";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "compare", label: "Compare Evidence", icon: <GitCompare size={14} /> },
  { id: "search",  label: "Database Search",  icon: <Search     size={14} /> },
  { id: "history", label: "Past Results",     icon: <History    size={14} /> },
];

export default function ComparePage() {
  const [activeTab, setActiveTab] = useState<TabId>("compare");

  return (
    <>
      <Head><title>Compare Evidence — ForensicEdge</title></Head>

      <AppLayout title="Compare Evidence">

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-gray-800 mb-6">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={clsx(
                "flex items-center gap-1.5 px-4 py-2.5 text-sm -mb-px border-b-2 transition-colors",
                activeTab === t.id
                  ? "border-white text-white font-medium"
                  : "border-transparent text-gray-500 hover:text-gray-300",
              )}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/*
          ComparePanel stays mounted even when other tabs are active so that
          upload state (images, result, feedback) is not lost on tab switch.
          The other two panels are lazy-mounted only when selected.
        */}
        <div className={activeTab === "compare" ? "contents" : "hidden"}>
          <ComparePanel />
        </div>
        {activeTab === "search"  && <DatabaseSearchPanel />}
        {activeTab === "history" && <PastResultsPanel    />}

      </AppLayout>
    </>
  );
}