/**
 * src/pages/cases.tsx
 * ─────────────────────
 * Case Management page.
 *
 * Features
 * ─────────
 *   List all cases accessible to the current user
 *   Create new case (inline expandable form)
 *   View full case detail (evidence, analyses, reports, notes)
 *   Update case status and priority
 *   Link evidence / analyses / reports to a case
 *   Add investigator notes
 *   Delete case (admin only)
 *
 * Workflow
 * ─────────
 *   1. Create case → fill title + description + priority
 *   2. Upload images on /upload page
 *   3. Come back here → open case → Link Evidence → select image ID
 *   4. Run comparison on /compare page
 *   5. Come back here → open case → Link Analysis → select result ID
 *   6. Generate report on /reports page
 *   7. Come back here → open case → Link Report → select report ID
 *   8. Post notes as the investigation progresses
 *   9. Update status: OPEN → IN_PROGRESS → REVIEW → CLOSED
 */

import { useState, useEffect, FormEvent } from "react";
import Head from "next/head";
import {
  FolderOpen, Plus, ChevronDown, ChevronUp,
  Trash2, Link as LinkIcon, StickyNote,
  AlertTriangle, CheckCircle, Clock, Archive,
} from "lucide-react";
import toast  from "react-hot-toast";
import clsx   from "clsx";

import AppLayout from "../components/layout/AppLayout";
import Card      from "../components/ui/Card";
import Button    from "../components/ui/Button";
import Input     from "../components/ui/Input";
import Badge     from "../components/ui/Badge";
import Spinner   from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import api from "../services/api";

// ── Types ────────────────────────────────────────────────────────────────────

type CaseStatus   = "OPEN" | "IN_PROGRESS" | "REVIEW" | "CLOSED";
type CasePriority = "LOW" | "MEDIUM" | "HIGH";

interface CaseSummary {
  id:             number;
  title:          string;
  description:    string | null;
  created_by:     number | null;
  assigned_to:    number | null;
  status:         CaseStatus;
  priority:       CasePriority;
  created_at:     string;
  updated_at:     string;
  evidence_count: number;
  analyses_count: number;
  reports_count:  number;
  notes_count:    number;
}

interface CaseNote        { id: number; user_id: number | null; note_text: string; created_at: string; }
interface CaseEvidenceItem{ id: number; image_id: number; linked_at: string; notes: string | null; }
interface CaseAnalysisItem{ id: number; result_id: number; added_at: string; }
interface CaseReportItem  { id: number; report_id: number; added_at: string; }

interface CaseDetail extends CaseSummary {
  evidence:  CaseEvidenceItem[];
  analyses:  CaseAnalysisItem[];
  reports:   CaseReportItem[];
  notes:     CaseNote[];
}

// ── Style helpers ─────────────────────────────────────────────────────────────

const STATUS_ICON: Record<CaseStatus, React.ReactNode> = {
  OPEN:        <Clock        size={14} className="text-blue-400"   />,
  IN_PROGRESS: <AlertTriangle size={14} className="text-yellow-400" />,
  REVIEW:      <CheckCircle  size={14} className="text-purple-400" />,
  CLOSED:      <Archive      size={14} className="text-gray-500"   />,
};

const STATUS_BADGE: Record<CaseStatus, "blue" | "yellow" | "red" | "green" | "gray"> = {
  OPEN:        "blue",
  IN_PROGRESS: "yellow",
  REVIEW:      "red",
  CLOSED:      "gray",
};

const PRIORITY_BADGE: Record<CasePriority, "green" | "yellow" | "red"> = {
  LOW:    "green",
  MEDIUM: "yellow",
  HIGH:   "red",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function CasesPage() {
  const { isAdmin } = useAuth();

  const [cases,      setCases]      = useState<CaseSummary[]>([]);
  const [total,      setTotal]      = useState(0);
  const [loading,    setLoading]    = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail,     setDetail]     = useState<CaseDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");

  // Create form
  const [title,       setTitle]       = useState("");
  const [description, setDescription] = useState("");
  const [priority,    setPriority]    = useState<CasePriority>("MEDIUM");
  const [creating,    setCreating]    = useState(false);

  // Link / note inputs
  const [linkImageId,  setLinkImageId]  = useState("");
  const [linkResultId, setLinkResultId] = useState("");
  const [linkReportId, setLinkReportId] = useState("");
  const [noteText,     setNoteText]     = useState("");
  const [linking,      setLinking]      = useState(false);

  // ── Load cases ──────────────────────────────────────────────────────────────
  const loadCases = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (statusFilter)   params.status_filter = statusFilter;
      if (priorityFilter) params.priority      = priorityFilter;

      const { data } = await api.get("/cases", { params });
      setCases(data.cases);
      setTotal(data.total);
    } catch {
      toast.error("Could not load cases.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadCases(); }, [statusFilter, priorityFilter]);

  // ── Expand / collapse case detail ───────────────────────────────────────────
  const toggleExpand = async (caseId: number) => {
    if (expandedId === caseId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(caseId);
    setDetail(null);
    setDetailLoading(true);
    try {
      const { data } = await api.get(`/cases/${caseId}`);
      setDetail(data);
    } catch {
      toast.error("Could not load case details.");
    } finally {
      setDetailLoading(false);
    }
  };

  const refreshDetail = async (caseId: number) => {
    try {
      const { data } = await api.get(`/cases/${caseId}`);
      setDetail(data);
      loadCases();
    } catch { /* ignore */ }
  };

  // ── Create case ─────────────────────────────────────────────────────────────
  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    try {
      await api.post("/cases", {
        title:       title.trim(),
        description: description.trim() || null,
        priority,
      });
      toast.success("Case created.");
      setTitle(""); setDescription(""); setPriority("MEDIUM");
      setShowCreate(false);
      loadCases();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Creation failed.";
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  };

  // ── Update status ───────────────────────────────────────────────────────────
  const handleStatusChange = async (caseId: number, newStatus: CaseStatus) => {
    try {
      await api.put(`/cases/${caseId}`, { status: newStatus });
      toast.success("Status updated.");
      loadCases();
      if (expandedId === caseId) refreshDetail(caseId);
    } catch {
      toast.error("Update failed.");
    }
  };

  // ── Delete ──────────────────────────────────────────────────────────────────
  const handleDelete = async (c: CaseSummary) => {
    if (!confirm(`Delete case "${c.title}"? Links will be removed but evidence and reports are kept.`)) return;
    try {
      await api.delete(`/cases/${c.id}`);
      toast.success("Case deleted.");
      if (expandedId === c.id) { setExpandedId(null); setDetail(null); }
      loadCases();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Delete failed.";
      toast.error(msg);
    }
  };

  // ── Link helpers ────────────────────────────────────────────────────────────
  const linkEvidence = async (caseId: number) => {
    if (!linkImageId.trim()) return;
    setLinking(true);
    try {
      await api.post(`/cases/${caseId}/evidence`, { image_id: parseInt(linkImageId) });
      toast.success("Evidence linked.");
      setLinkImageId("");
      refreshDetail(caseId);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Link failed.";
      toast.error(msg);
    } finally { setLinking(false); }
  };

  const linkAnalysis = async (caseId: number) => {
    if (!linkResultId.trim()) return;
    setLinking(true);
    try {
      await api.post(`/cases/${caseId}/analyses`, { result_id: parseInt(linkResultId) });
      toast.success("Analysis linked.");
      setLinkResultId("");
      refreshDetail(caseId);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Link failed.";
      toast.error(msg);
    } finally { setLinking(false); }
  };

  const linkReport = async (caseId: number) => {
    if (!linkReportId.trim()) return;
    setLinking(true);
    try {
      await api.post(`/cases/${caseId}/reports`, { report_id: parseInt(linkReportId) });
      toast.success("Report linked.");
      setLinkReportId("");
      refreshDetail(caseId);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Link failed.";
      toast.error(msg);
    } finally { setLinking(false); }
  };

  const addNote = async (caseId: number) => {
    if (!noteText.trim()) return;
    setLinking(true);
    try {
      await api.post(`/cases/${caseId}/notes`, { note_text: noteText.trim() });
      toast.success("Note added.");
      setNoteText("");
      refreshDetail(caseId);
    } catch {
      toast.error("Could not add note.");
    } finally { setLinking(false); }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <>
      <Head><title>Cases — ForensicEdge</title></Head>
      <AppLayout title="Case Management">

        {/* ── Page header ────────────────────────────────────────────────── */}
        <div className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-white font-semibold text-lg">Cases</h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {loading ? "Loading…" : `${total} investigation case${total !== 1 ? "s" : ""}`}
            </p>
          </div>
          <Button
            size="sm"
            icon={showCreate ? <ChevronUp size={14} /> : <Plus size={14} />}
            onClick={() => setShowCreate((v) => !v)}
          >
            {showCreate ? "Cancel" : "New case"}
          </Button>
        </div>

        {/* ── Create form ────────────────────────────────────────────────── */}
        {showCreate && (
          <Card title="Create new case">
            <form onSubmit={handleCreate} className="space-y-4">
              <Input
                label="Case title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Case #2025-001 Robbery Scene"
                required minLength={3}
                disabled={creating}
              />
              <div>
                <label className="field-label">Description (optional)</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="Context, location, suspect details…"
                  className="field resize-none"
                  disabled={creating}
                />
              </div>
              <div>
                <label className="field-label">Priority</label>
                <select
                  aria-label="field-label"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as CasePriority)}
                  className="field"
                  disabled={creating}
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                </select>
              </div>
              <Button type="submit" loading={creating}>Create case</Button>
            </form>
          </Card>
        )}

        {/* ── Filters ────────────────────────────────────────────────────── */}
        <div className="flex gap-3 flex-wrap">
          <select
            aria-label="Status filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="field text-sm w-auto"
          >
            <option value="">All statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In progress</option>
            <option value="REVIEW">Review</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            aria-label="Status filter"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="field text-sm w-auto"
          >
            <option value="">All priorities</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
        </div>

        {/* ── Cases list ─────────────────────────────────────────────────── */}
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>

        ) : cases.length === 0 ? (
          <Card className="text-center py-16 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center
                            justify-center mx-auto">
              <FolderOpen size={28} className="text-gray-600" />
            </div>
            <p className="text-gray-300 font-medium">No cases yet</p>
            <p className="text-gray-600 text-sm">
              Create a case to start organising your investigation.
            </p>
          </Card>

        ) : (
          <div className="space-y-3">
            {cases.map((c) => (
              <div key={c.id} className="bg-gray-900 border border-gray-800
                                         rounded-2xl overflow-hidden">

                {/* ── Case header row ─────────────────────────────────── */}
                <div className="flex items-start gap-4 p-5">

                  {/* Status icon */}
                  <div className="mt-1 shrink-0">{STATUS_ICON[c.status]}</div>

                  {/* Title + badges */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-white font-medium truncate">{c.title}</p>
                      <Badge variant={STATUS_BADGE[c.status]}>
                        {c.status.replace("_", " ")}
                      </Badge>
                      <Badge variant={PRIORITY_BADGE[c.priority]}>
                        {c.priority}
                      </Badge>
                    </div>

                    {c.description && (
                      <p className="text-gray-500 text-xs mt-1 line-clamp-1">
                        {c.description}
                      </p>
                    )}

                    {/* Counts */}
                    <div className="flex gap-4 mt-2 text-xs text-gray-600">
                      <span>{c.evidence_count} evidence</span>
                      <span>{c.analyses_count} analyses</span>
                      <span>{c.reports_count} reports</span>
                      <span>{c.notes_count} notes</span>
                      <span className="text-gray-700">
                        {new Date(c.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    {/* Status selector */}
                    <select
                      value={c.status}
                      onChange={(e) =>
                        handleStatusChange(c.id, e.target.value as CaseStatus)
                      }
                      className="field text-xs py-1 px-2 w-auto"
                      title="Change status"
                    >
                      <option value="OPEN">Open</option>
                      <option value="IN_PROGRESS">In progress</option>
                      <option value="REVIEW">Review</option>
                      <option value="CLOSED">Closed</option>
                    </select>

                    {/* Expand */}
                    <button
                      onClick={() => toggleExpand(c.id)}
                      className="p-1.5 rounded-lg text-gray-500 hover:text-white
                                 hover:bg-gray-800 transition-colors"
                      title="View details"
                    >
                      {expandedId === c.id
                        ? <ChevronUp   size={16} />
                        : <ChevronDown size={16} />}
                    </button>

                    {/* Delete (admin only) */}
                    {isAdmin() && (
                      <button
                        onClick={() => handleDelete(c)}
                        className="p-1.5 rounded-lg text-gray-500 hover:text-red-400
                                   hover:bg-gray-800 transition-colors"
                        title="Delete case"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                </div>

                {/* ── Expanded detail panel ───────────────────────────── */}
                {expandedId === c.id && (
                  <div className="border-t border-gray-800 px-5 pb-5 pt-4 space-y-5">

                    {detailLoading ? (
                      <div className="flex justify-center py-6"><Spinner /></div>
                    ) : detail ? (
                      <>
                        {/* Evidence */}
                        <DetailSection
                          title="Evidence"
                          icon={<LinkIcon size={14} className="text-blue-400" />}
                          count={detail.evidence.length}
                        >
                          {detail.evidence.map((ev) => (
                            <DetailItem key={ev.id}
                              label={`Image #${ev.image_id}`}
                              sub={ev.notes ?? undefined}
                              date={ev.linked_at}
                            />
                          ))}
                          <LinkInput
                            placeholder="Image ID (from Upload page)"
                            value={linkImageId}
                            onChange={setLinkImageId}
                            onLink={() => linkEvidence(c.id)}
                            loading={linking}
                          />
                        </DetailSection>

                        {/* Analyses */}
                        <DetailSection
                          title="Analyses"
                          icon={<LinkIcon size={14} className="text-purple-400" />}
                          count={detail.analyses.length}
                        >
                          {detail.analyses.map((an) => (
                            <DetailItem key={an.id}
                              label={`Result #${an.result_id}`}
                              date={an.added_at}
                            />
                          ))}
                          <LinkInput
                            placeholder="Result ID (from Compare page)"
                            value={linkResultId}
                            onChange={setLinkResultId}
                            onLink={() => linkAnalysis(c.id)}
                            loading={linking}
                          />
                        </DetailSection>

                        {/* Reports */}
                        <DetailSection
                          title="Reports"
                          icon={<LinkIcon size={14} className="text-green-400" />}
                          count={detail.reports.length}
                        >
                          {detail.reports.map((rp) => (
                            <DetailItem key={rp.id}
                              label={`Report #${rp.report_id}`}
                              date={rp.added_at}
                            />
                          ))}
                          <LinkInput
                            placeholder="Report ID (from Reports page)"
                            value={linkReportId}
                            onChange={setLinkReportId}
                            onLink={() => linkReport(c.id)}
                            loading={linking}
                          />
                        </DetailSection>

                        {/* Notes */}
                        <DetailSection
                          title="Notes"
                          icon={<StickyNote size={14} className="text-yellow-400" />}
                          count={detail.notes.length}
                        >
                          {detail.notes.map((n) => (
                            <div key={n.id}
                              className="bg-gray-800/50 rounded-lg px-3 py-2 space-y-1">
                              <p className="text-gray-200 text-sm">{n.note_text}</p>
                              <p className="text-gray-600 text-xs">
                                {new Date(n.created_at).toLocaleString()}
                              </p>
                            </div>
                          ))}
                          {/* Add note */}
                          <div className="flex gap-2">
                            <input
                              value={noteText}
                              onChange={(e) => setNoteText(e.target.value)}
                              placeholder="Add a note…"
                              className="field flex-1 text-sm py-1.5"
                            />
                            <Button
                              size="sm"
                              loading={linking}
                              onClick={() => addNote(c.id)}
                            >
                              Add
                            </Button>
                          </div>
                        </DetailSection>
                      </>
                    ) : null}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

      </AppLayout>
    </>
  );
}


// ── Sub-components ────────────────────────────────────────────────────────────

function DetailSection({
  title, icon, count, children,
}: {
  title: string; icon: React.ReactNode;
  count: number; children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {icon}
        <p className="text-gray-400 text-xs font-medium uppercase tracking-wide">
          {title}
        </p>
        <span className="badge-gray text-xs">{count}</span>
      </div>
      <div className="space-y-2 ml-5">
        {children}
      </div>
    </div>
  );
}

function DetailItem({
  label, sub, date,
}: { label: string; sub?: string; date: string }) {
  return (
    <div className="flex items-center justify-between bg-gray-800/40
                    rounded-lg px-3 py-1.5 text-sm">
      <div>
        <span className="text-gray-200">{label}</span>
        {sub && <span className="text-gray-500 text-xs ml-2">{sub}</span>}
      </div>
      <span className="text-gray-600 text-xs">
        {new Date(date).toLocaleDateString()}
      </span>
    </div>
  );
}

function LinkInput({
  placeholder, value, onChange, onLink, loading,
}: {
  placeholder: string; value: string;
  onChange: (v: string) => void;
  onLink: () => void; loading: boolean;
}) {
  return (
    <div className="flex gap-2">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="field flex-1 text-sm py-1.5"
        type="number"
        min={1}
      />
      <Button size="sm" loading={loading} onClick={onLink}
              icon={<LinkIcon size={13} />}>
        Link
      </Button>
    </div>
  );
}