/**
 * src/pages/feedback.tsx
 * ────────────────────────
 * Feedback history page.
 *
 * Access by role
 * ───────────────
 *   analyst     — sees an informational message directing them to the
 *                 Compare page to submit feedback (they cannot list all feedback)
 *   admin / ai_engineer — see the full feedback table with summary stats,
 *                         filter by is_correct, and export button
 *
 * Why analysts can't list feedback here
 * ───────────────────────────────────────
 * GET /feedback is restricted to admin and ai_engineer by the backend.
 * Analysts submit feedback from the Compare page result card.
 * This page is their reminder of where to do that.
 */

import { useState, useEffect } from "react";
import Head   from "next/head";
import Link   from "next/link";
import { MessageSquare, ThumbsUp, ThumbsDown, Download } from "lucide-react";
import toast  from "react-hot-toast";
import clsx   from "clsx";

import AppLayout from "../components/layout/AppLayout";
import Card      from "../components/ui/Card";
import { StatCard } from "../components/ui/Card";
import Button    from "../components/ui/Button";
import Spinner   from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { feedbackService, FeedbackResponse } from "../services/feedbackService";

const LIMIT = 30;

export default function FeedbackPage() {
  const { isAdmin, isAIEngineer } = useAuth();
  const canSeeAll = isAdmin() || isAIEngineer();

  const [feedback,  setFeedback]  = useState<FeedbackResponse[]>([]);
  const [total,     setTotal]     = useState(0);
  const [correct,   setCorrect]   = useState<number | null>(null);
  const [incorrect, setIncorrect] = useState<number | null>(null);
  const [page,      setPage]      = useState(1);
  const [filter,    setFilter]    = useState<boolean | undefined>(undefined);
  const [loading,   setLoading]   = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!canSeeAll) { setLoading(false); return; }
    setLoading(true);
    feedbackService
      .list({ isCorrect: filter, page, limit: LIMIT })
      .then((res) => {
        setFeedback(res.feedback);
        setTotal(res.total);
        setCorrect(res.total_correct);
        setIncorrect(res.total_incorrect);
      })
      .finally(() => setLoading(false));
  }, [canSeeAll, filter, page]);

  const handleFilterChange = (value: boolean | undefined) => {
    setFilter(value);
    setPage(1);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const records = await feedbackService.exportIncorrect();
      // Download as JSON file
      const blob   = new Blob([JSON.stringify(records, null, 2)], { type: "application/json" });
      const url    = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href     = url;
      anchor.download = `incorrect_feedback_export.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      toast.success(`Exported ${records.length} incorrect feedback records.`);
    } catch {
      toast.error("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <>
      <Head><title>Feedback — ForensicEdge</title></Head>

      <AppLayout title="Feedback">

        {/* ── Non-admin view ────────────────────────────────────────────── */}
        {!canSeeAll ? (
          <Card className="text-center py-16 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center
                            justify-center mx-auto">
              <MessageSquare size={28} className="text-gray-600" />
            </div>
            <div>
              <p className="text-gray-300 font-medium">Submit Feedback from Compare</p>
              <p className="text-gray-600 text-sm mt-1 max-w-sm mx-auto">
                After running a comparison, use the thumbs up or thumbs down
                buttons on the result card to flag whether the AI result was correct.
              </p>
            </div>
            <Link href="/compare">
              <Button size="sm" icon={<MessageSquare size={14} />}>
                Go to Compare
              </Button>
            </Link>
          </Card>

        ) : (
          /* ── Admin / AI engineer view ─────────────────────────────────── */
          <>
            {/* Page header */}
            <div className="flex items-end justify-between flex-wrap gap-3">
              <div>
                <h2 className="text-white font-semibold text-lg">
                  All Feedback
                </h2>
                <p className="text-gray-500 text-sm mt-0.5">
                  Investigator feedback on similarity results
                </p>
              </div>

              {/* Export button — AI engineers use this for retraining */}
              <Button
                variant="secondary"
                size="sm"
                icon={<Download size={14} />}
                loading={exporting}
                onClick={handleExport}
              >
                Export incorrect cases
              </Button>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-3 gap-4">
              <StatCard
                label="Total feedback"
                value={loading ? null : total}
                icon={<MessageSquare size={18} className="text-blue-400" />}
              />
              <StatCard
                label="Correct"
                value={loading ? null : correct}
                icon={<ThumbsUp size={18} className="text-green-400" />}
              />
              <StatCard
                label="Incorrect"
                value={loading ? null : incorrect}
                icon={<ThumbsDown size={18} className="text-red-400" />}
              />
            </div>

            {/* Filter tabs */}
            <div className="flex gap-2">
              {[
                { label: "All",       value: undefined },
                { label: "Correct",   value: true      },
                { label: "Incorrect", value: false     },
              ].map((opt) => (
                <button
                  key={String(opt.label)}
                  onClick={() => handleFilterChange(opt.value)}
                  className={clsx(
                    "px-4 py-1.5 rounded-lg text-sm border transition-colors",
                    filter === opt.value
                      ? "bg-blue-600 border-blue-500 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white",
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Table */}
            {loading ? (
              <div className="flex justify-center py-12">
                <Spinner size="lg" />
              </div>

            ) : feedback.length === 0 ? (
              <Card className="text-center py-12 space-y-2">
                <p className="text-gray-500 text-sm">No feedback records found.</p>
                {filter !== undefined && (
                  <button
                    onClick={() => handleFilterChange(undefined)}
                    className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
                  >
                    Show all feedback
                  </button>
                )}
              </Card>

            ) : (
              <Card padding="p-0">
                <div className="overflow-x-auto">
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th className="w-10">#</th>
                        <th>Result ID</th>
                        <th>Verdict</th>
                        <th>Comment</th>
                        <th className="whitespace-nowrap">Submitted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {feedback.map((fb) => (
                        <tr key={fb.id}>
                          <td className="text-gray-600 text-xs tabular-nums">
                            {fb.id}
                          </td>
                          <td className="font-mono text-sm">
                            #{fb.result_id}
                          </td>
                          <td>
                            {fb.is_correct ? (
                              <span className="flex items-center gap-1.5 text-green-400 text-xs font-medium">
                                <ThumbsUp size={12} />
                                Correct
                              </span>
                            ) : (
                              <span className="flex items-center gap-1.5 text-red-400 text-xs font-medium">
                                <ThumbsDown size={12} />
                                Incorrect
                              </span>
                            )}
                          </td>
                          <td>
                            <span
                              className="block truncate max-w-[280px] text-gray-400 text-xs"
                              title={fb.comment ?? undefined}
                            >
                              {fb.comment ?? (
                                <span className="text-gray-700 italic">No comment</span>
                              )}
                            </span>
                          </td>
                          <td className="text-gray-500 text-xs whitespace-nowrap">
                            {new Date(fb.created_at).toLocaleDateString(undefined, {
                              month: "short",
                              day:   "numeric",
                              year:  "numeric",
                            })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3">
                <Button
                  variant="secondary" size="sm"
                  disabled={page === 1 || loading}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <span className="text-gray-500 text-sm tabular-nums">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="secondary" size="sm"
                  disabled={page >= totalPages || loading}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}

      </AppLayout>
    </>
  );
}