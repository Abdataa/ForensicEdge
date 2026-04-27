/**
 * src/pages/cases.tsx
 * ─────────────────────
 * Case Management page — list, create, view, and manage investigations.
 */

import { useState, useEffect, FormEvent } from "react";
import Head    from "next/head";
import {
  FolderOpen, Plus, X, ChevronRight,
  FileText, GitCompare, Upload,
  MessageSquare, Clock, CheckCircle,
  RefreshCw, Eye,
} from "lucide-react";
import toast   from "react-hot-toast";
import clsx    from "clsx";

import AppLayout from "../components/layout/AppLayout";
import Card      from "../components/ui/Card";
import Button    from "../components/ui/Button";
import Input     from "../components/ui/Input";
import Modal     from "../components/ui/modal";
import Spinner   from "../components/ui/Spinner";
import api       from "../services/api";

// ── Types ────────────────────────────────────────────────────────────────────

type CaseStatus   = "OPEN" | "IN_PROGRESS" | "REVIEW" | "CLOSED";
type CasePriority = "LOW"  | "MEDIUM"      | "HIGH";

interface CaseResponse {
  id: number; title: string; description: string | null;
  created_by: number | null; assigned_to: number | null;
  status: CaseStatus; priority: CasePriority;
  created_at: string; updated_at: string;
  evidence_count: number; analyses_count: number;
  reports_count: number;  notes_count: number;
}

interface CaseNote {
  id: number; case_id: number; user_id: number | null;
  note_text: string; created_at: string;
}
interface CaseEvidenceItem {
  id: number; case_id: number; image_id: number;
  linked_by: number | null; linked_at: string; notes: string | null;
}
interface CaseAnalysisItem {
  id: number; case_id: number; result_id: number; added_at: string;
}
interface CaseReportItem {
  id: number; case_id: number; report_id: number; added_at: string;
}
interface CaseDetail extends CaseResponse {
  evidence: CaseEvidenceItem[];
  analyses: CaseAnalysisItem[];
  reports:  CaseReportItem[];
  notes:    CaseNote[];
}

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CFG: Record<CaseStatus, { colour: string; bg: string; icon: React.ReactNode; label: string }> = {
  OPEN:        { colour: "text-blue-400",   bg: "bg-blue-950/60 border-blue-800",    icon: <FolderOpen size={11} />, label: "Open" },
  IN_PROGRESS: { colour: "text-yellow-400", bg: "bg-yellow-950/60 border-yellow-800",icon: <RefreshCw  size={11} />, label: "In Progress" },
  REVIEW:      { colour: "text-purple-400", bg: "bg-purple-950/60 border-purple-800",icon: <Eye        size={11} />, label: "Review" },
  CLOSED:      { colour: "text-green-400",  bg: "bg-green-950/60 border-green-800",  icon: <CheckCircle size={11} />, label: "Closed" },
};

const PRIORITY_CLR: Record<CasePriority, string> = {
  LOW: "text-gray-400", MEDIUM: "text-yellow-400", HIGH: "text-red-400",
};

const STATUS_TABS = [
  { label: "All",         value: "" },
  { label: "Open",        value: "OPEN" },
  { label: "In Progress", value: "IN_PROGRESS" },
  { label: "Review",      value: "REVIEW" },
  { label: "Closed",      value: "CLOSED" },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function CasesPage() {
  const [cases,       setCases]       = useState<CaseResponse[]>([]);
  const [total,       setTotal]       = useState(0);
  const [loading,     setLoading]     = useState(true);
  const [filter,      setFilter]      = useState("");
  const [showCreate,  setShowCreate]  = useState(false);
  const [newTitle,    setNewTitle]    = useState("");
  const [newDesc,     setNewDesc]     = useState("");
  const [newPriority, setNewPriority] = useState<CasePriority>("MEDIUM");
  const [creating,    setCreating]    = useState(false);
  const [selected,    setSelected]    = useState<CaseDetail | null>(null);
  const [detailLoad,  setDetailLoad]  = useState(false);
  const [noteText,    setNoteText]    = useState("");
  const [addingNote,  setAddingNote]  = useState(false);
  const [linkImg,     setLinkImg]     = useState("");
  const [linkRes,     setLinkRes]     = useState("");
  const [linkRep,     setLinkRep]     = useState("");
  const [linking,     setLinking]     = useState(false);

  const loadCases = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/cases", {
        params: { status_filter: filter || undefined, limit: 50 },
      });
      setCases(data.cases); setTotal(data.total);
    } catch { toast.error("Could not load cases."); }
    finally  { setLoading(false); }
  };

  useEffect(() => { loadCases(); }, [filter]);

  const openCase = async (id: number) => {
    setDetailLoad(true); setSelected(null);
    try {
      const { data } = await api.get<CaseDetail>(`/cases/${id}`);
      setSelected(data);
    } catch { toast.error("Could not load case details."); }
    finally  { setDetailLoad(false); }
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/cases", {
        title: newTitle.trim(),
        description: newDesc.trim() || null,
        priority: newPriority,
      });
      toast.success("Case created.");
      setShowCreate(false); setNewTitle(""); setNewDesc(""); setNewPriority("MEDIUM");
      loadCases();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed.");
    } finally { setCreating(false); }
  };

  const changeStatus = async (caseId: number, s: CaseStatus) => {
    try {
      await api.put(`/cases/${caseId}`, { status: s });
      toast.success("Status updated.");
      loadCases();
      if (selected?.id === caseId) openCase(caseId);
    } catch { toast.error("Update failed."); }
  };

  const handleNote = async () => {
    if (!selected || !noteText.trim()) return;
    setAddingNote(true);
    try {
      await api.post(`/cases/${selected.id}/notes`, { note_text: noteText.trim() });
      toast.success("Note added."); setNoteText(""); openCase(selected.id);
    } catch { toast.error("Could not add note."); }
    finally  { setAddingNote(false); }
  };

  const link = async (endpoint: string, body: object, reset: () => void) => {
    if (!selected) return;
    setLinking(true);
    try {
      await api.post(`/cases/${selected.id}/${endpoint}`, body);
      toast.success("Linked."); reset(); openCase(selected.id);
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Link failed.");
    } finally { setLinking(false); }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <Head><title>Cases — ForensicEdge</title></Head>
      <AppLayout title="Case Management">

        {/* Header */}
        <div className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-white font-semibold text-lg">Investigations</h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {loading ? "Loading…" : `${total} case${total !== 1 ? "s" : ""}`}
            </p>
          </div>
          <Button size="sm" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>
            New case
          </Button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 flex-wrap">
          {STATUS_TABS.map((t) => (
            <button key={t.value} onClick={() => setFilter(t.value)}
              className={clsx(
                "px-4 py-1.5 rounded-lg text-sm border transition-colors",
                filter === t.value
                  ? "bg-blue-600 border-blue-500 text-white"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white",
              )}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Case grid */}
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : cases.length === 0 ? (
          <Card className="text-center py-16 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mx-auto">
              <FolderOpen size={28} className="text-gray-600" />
            </div>
            <p className="text-gray-400 font-medium">No cases found</p>
            <p className="text-gray-600 text-sm">
              {filter ? `No ${filter.replace("_"," ").toLowerCase()} cases.`
                      : "Create your first investigation case."}
            </p>
            <Button size="sm" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>
              Create case
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cases.map((c) => {
              const cfg = STATUS_CFG[c.status];
              return (
                <div key={c.id} onClick={() => openCase(c.id)}
                  className="card cursor-pointer border hover:border-gray-600 transition-all space-y-4">
                  <div className="flex items-center justify-between">
                    <span className={clsx(
                      "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full",
                      "text-xs font-medium border", cfg.colour, cfg.bg,
                    )}>
                      {cfg.icon} {cfg.label}
                    </span>
                    <span className={clsx("text-xs font-medium", PRIORITY_CLR[c.priority])}>
                      {c.priority}
                    </span>
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm leading-snug">{c.title}</p>
                    {c.description && (
                      <p className="text-gray-500 text-xs mt-1 line-clamp-2">{c.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><Upload size={11}/> {c.evidence_count}</span>
                    <span className="flex items-center gap-1"><GitCompare size={11}/> {c.analyses_count}</span>
                    <span className="flex items-center gap-1"><FileText size={11}/> {c.reports_count}</span>
                    <span className="flex items-center gap-1"><MessageSquare size={11}/> {c.notes_count}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-600">
                    <span className="flex items-center gap-1">
                      <Clock size={10}/> {new Date(c.created_at).toLocaleDateString()}
                    </span>
                    <ChevronRight size={14} className="text-gray-700" />
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </AppLayout>

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create new case">
        <form onSubmit={handleCreate} className="space-y-4">
          <Input label="Case title" value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Case #2025-001 Robbery Scene"
            required minLength={3} disabled={creating} />
          <div className="space-y-1.5">
            <label className="field-label">Description (optional)</label>
            <textarea value={newDesc} onChange={(e) => setNewDesc(e.target.value)}
              rows={3} placeholder="Context or initial observations…"
              className="field resize-none" disabled={creating} />
          </div>
          <div className="space-y-1.5">
            <label className="field-label">Priority</label>
            <select value={newPriority}
              aria-label="Select case priority"
              onChange={(e) => setNewPriority(e.target.value as CasePriority)}
              className="field" disabled={creating}>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
            </select>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" fullWidth type="button"
              onClick={() => setShowCreate(false)} disabled={creating}>Cancel</Button>
            <Button fullWidth type="submit" loading={creating}>Create case</Button>
          </div>
        </form>
      </Modal>

      {/* Detail drawer */}
      {(detailLoad || selected) && (
        <div className="fixed inset-0 z-40 flex justify-end">
          <div className="absolute inset-0 bg-black/50" onClick={() => setSelected(null)} />
          <div className="relative w-full max-w-xl bg-gray-900 border-l border-gray-700
                          flex flex-col h-full overflow-hidden shadow-2xl">

            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 shrink-0">
              <h2 className="text-white font-semibold text-base truncate">
                {selected ? selected.title : "Loading…"}
              </h2>
              <button onClick={() => setSelected(null)}
                aria-label="Close details"
                className="text-gray-500 hover:text-white transition-colors p-1">
                <X size={18} />
              </button>
            </div>

            {detailLoad ? (
              <div className="flex-1 flex items-center justify-center"><Spinner size="lg" /></div>
            ) : selected && (
              <div className="flex-1 overflow-y-auto p-6 space-y-6">

                {/* Overview */}
                <section className="space-y-3">
                  <h3 className="section-title">Overview</h3>
                  <div className="flex items-start gap-2 flex-wrap">
                    <p className="text-gray-500 text-xs w-16 pt-1">Status:</p>
                    <div className="flex gap-2 flex-wrap">
                      {(["OPEN","IN_PROGRESS","REVIEW","CLOSED"] as CaseStatus[]).map((s) => {
                        const cfg = STATUS_CFG[s];
                        return (
                          <button key={s} onClick={() => changeStatus(selected.id, s)}
                            className={clsx(
                              "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border transition-all",
                              selected.status === s ? clsx(cfg.colour, cfg.bg)
                                : "text-gray-500 border-gray-700 hover:border-gray-500",
                            )}>
                            {cfg.icon} {cfg.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <p className="text-gray-600 mb-0.5">Priority</p>
                      <p className={clsx("font-medium", PRIORITY_CLR[selected.priority])}>
                        {selected.priority}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600 mb-0.5">Created</p>
                      <p className="text-gray-300">{new Date(selected.created_at).toLocaleString()}</p>
                    </div>
                  </div>
                  {selected.description && (
                    <p className="text-gray-400 text-sm leading-relaxed">{selected.description}</p>
                  )}
                </section>

                {/* Evidence */}
                <section className="space-y-3">
                  <h3 className="section-title">Evidence ({selected.evidence.length})</h3>
                  {selected.evidence.length === 0
                    ? <p className="text-gray-600 text-sm">No evidence linked yet.</p>
                    : selected.evidence.map((e) => (
                        <div key={e.id} className="flex justify-between items-center
                          bg-gray-800 rounded-lg px-3 py-2 text-sm">
                          <span className="text-gray-300 flex items-center gap-1.5">
                            <Upload size={12} className="text-blue-400" /> Image #{e.image_id}
                          </span>
                          <span className="text-gray-600 text-xs">
                            {new Date(e.linked_at).toLocaleDateString()}
                          </span>
                        </div>
                      ))
                  }
                  <div className="flex gap-2">
                    <input type="number" value={linkImg} min={1}
                      onChange={(e) => setLinkImg(e.target.value)}
                      placeholder="Image ID" className="field text-sm flex-1" />
                    <Button size="sm" loading={linking} disabled={!linkImg}
                      onClick={() => link("evidence", { image_id: parseInt(linkImg) }, () => setLinkImg(""))}
                      icon={<Plus size={13} />}>Link</Button>
                  </div>
                </section>

                {/* Analyses */}
                <section className="space-y-3">
                  <h3 className="section-title">Analyses ({selected.analyses.length})</h3>
                  {selected.analyses.length === 0
                    ? <p className="text-gray-600 text-sm">No analyses linked yet.</p>
                    : selected.analyses.map((a) => (
                        <div key={a.id} className="flex justify-between items-center
                          bg-gray-800 rounded-lg px-3 py-2 text-sm">
                          <span className="text-gray-300 flex items-center gap-1.5">
                            <GitCompare size={12} className="text-purple-400"/> Result #{a.result_id}
                          </span>
                          <span className="text-gray-600 text-xs">
                            {new Date(a.added_at).toLocaleDateString()}
                          </span>
                        </div>
                      ))
                  }
                  <div className="flex gap-2">
                    <input type="number" value={linkRes} min={1}
                      onChange={(e) => setLinkRes(e.target.value)}
                      placeholder="Result ID" className="field text-sm flex-1" />
                    <Button size="sm" loading={linking} disabled={!linkRes}
                      onClick={() => link("analyses", { result_id: parseInt(linkRes) }, () => setLinkRes(""))}
                      icon={<Plus size={13} />}>Link</Button>
                  </div>
                </section>

                {/* Reports */}
                <section className="space-y-3">
                  <h3 className="section-title">Reports ({selected.reports.length})</h3>
                  {selected.reports.length === 0
                    ? <p className="text-gray-600 text-sm">No reports linked yet.</p>
                    : selected.reports.map((r) => (
                        <div key={r.id} className="flex justify-between items-center
                          bg-gray-800 rounded-lg px-3 py-2 text-sm">
                          <span className="text-gray-300 flex items-center gap-1.5">
                            <FileText size={12} className="text-green-400"/> Report #{r.report_id}
                          </span>
                          <span className="text-gray-600 text-xs">
                            {new Date(r.added_at).toLocaleDateString()}
                          </span>
                        </div>
                      ))
                  }
                  <div className="flex gap-2">
                    <input type="number" value={linkRep} min={1}
                      onChange={(e) => setLinkRep(e.target.value)}
                      placeholder="Report ID" className="field text-sm flex-1" />
                    <Button size="sm" loading={linking} disabled={!linkRep}
                      onClick={() => link("reports", { report_id: parseInt(linkRep) }, () => setLinkRep(""))}
                      icon={<Plus size={13} />}>Link</Button>
                  </div>
                </section>

                {/* Notes */}
                <section className="space-y-3">
                  <h3 className="section-title">Notes ({selected.notes.length})</h3>
                  {selected.notes.length === 0
                    ? <p className="text-gray-600 text-sm">No notes yet.</p>
                    : selected.notes.map((n) => (
                        <div key={n.id} className="bg-gray-800 border border-gray-700
                          rounded-xl px-4 py-3 space-y-1">
                          <p className="text-gray-200 text-sm leading-relaxed">{n.note_text}</p>
                          <p className="text-gray-600 text-xs flex items-center gap-1">
                            <MessageSquare size={10}/>
                            {new Date(n.created_at).toLocaleString()}
                          </p>
                        </div>
                      ))
                  }
                  <textarea value={noteText} onChange={(e) => setNoteText(e.target.value)}
                    rows={3} placeholder="Add an observation or note…"
                    className="field resize-none text-sm" disabled={addingNote} />
                  <Button size="sm" fullWidth loading={addingNote}
                    disabled={!noteText.trim()} onClick={handleNote}
                    icon={<MessageSquare size={13} />}>
                    Add note
                  </Button>
                </section>

              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}