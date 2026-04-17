"use client";
import { useEffect, useState } from "react";
import { MessageSquare, ThumbsUp, ThumbsDown } from "lucide-react";

import Navbar  from "../../../components/layout/Navbar";
import Card    from "../../../components/ui/Card";
import Table   from "../../../components/ui/Table";
import Button  from "../../../components/ui/Button";
import Spinner from "../../../components/ui/Spinner";
import { useAuth } from "../../../hooks/useAuth";
import { feedbackService, FeedbackResponse } from "../../../services/feedbackService";

const LIMIT = 30;

export default function FeedbackPage() {
  const { isAdmin, isAIEngineer } = useAuth();
  const canSeeAll                 = isAdmin() || isAIEngineer();

  const [feedback, setFeedback]   = useState<FeedbackResponse[]>([]);
  const [total,    setTotal]      = useState(0);
  const [correct,  setCorrect]    = useState<number | null>(null);
  const [incorrect,setIncorrect]  = useState<number | null>(null);
  const [page,     setPage]       = useState(1);
  const [filter,   setFilter]     = useState<boolean | undefined>(undefined);
  const [loading,  setLoading]    = useState(true);

  useEffect(() => {
    if (!canSeeAll) { setLoading(false); return; }
    setLoading(true);
    feedbackService.list({ is_correct: filter, page, limit: LIMIT })
      .then((res) => {
        setFeedback(res.feedback);
        setTotal(res.total);
        setCorrect(res.total_correct);
        setIncorrect(res.total_incorrect);
      })
      .finally(() => setLoading(false));
  }, [canSeeAll, filter, page]);

  const pages = Math.ceil(total / LIMIT);

  return (
    <>
      <Navbar title="Feedback" />
      <main className="page-body">

        <div>
          <h2 className="text-white font-semibold text-lg">
            {canSeeAll ? "All Feedback" : "Feedback"}
          </h2>
          <p className="text-gray-500 text-sm mt-0.5">
            Investigator feedback drives model retraining improvements.
          </p>
        </div>

        {/* Summary stats (admin/AI engineer) */}
        {canSeeAll && (
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Total",     value: total,     color: "text-white"       },
              { label: "Correct",   value: correct,   color: "text-green-400"   },
              { label: "Incorrect", value: incorrect, color: "text-red-400"     },
            ].map((s) => (
              <div key={s.label} className="stat-card">
                <p className="stat-label">{s.label}</p>
                <p className={`stat-value ${s.color}`}>{s.value ?? "—"}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filter tabs */}
        {canSeeAll && (
          <div className="flex gap-2">
            {[
              { label: "All",       value: undefined },
              { label: "Correct",   value: true      },
              { label: "Incorrect", value: false     },
            ].map((f) => (
              <button
                key={String(f.label)}
                onClick={() => { setFilter(f.value); setPage(1); }}
                className={`px-4 py-1.5 rounded-lg text-sm border transition-colors
                  ${filter === f.value
                    ? "bg-blue-600 border-blue-500 text-white"
                    : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white"}`}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}

        {/* Non-admin message */}
        {!canSeeAll && (
          <Card className="text-center py-12 space-y-3">
            <MessageSquare size={36} className="text-gray-700 mx-auto" />
            <p className="text-gray-400 text-sm">
              Submit feedback from the Compare page after running an analysis.
            </p>
            <p className="text-gray-600 text-xs">
              Use the thumbs up / thumbs down buttons on any result card.
            </p>
          </Card>
        )}

        {/* Feedback table */}
        {canSeeAll && (
          loading ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : (
            <Card>
              <Table
                keyField="id"
                data={feedback}
                columns={[
                  { key: "id",      header: "#",        render: (f) => <span className="text-gray-600">{f.id}</span> },
                  { key: "result",  header: "Result ID",render: (f) => f.result_id },
                  { key: "verdict", header: "Verdict",  render: (f) => (
                    f.is_correct ? (
                      <span className="flex items-center gap-1 text-green-400 text-xs">
                        <ThumbsUp size={12} /> Correct
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-400 text-xs">
                        <ThumbsDown size={12} /> Incorrect
                      </span>
                    )
                  )},
                  { key: "comment", header: "Comment",  render: (f) => (
                    <span className="text-gray-400 text-xs truncate max-w-[220px] block">
                      {f.comment ?? <span className="text-gray-700">—</span>}
                    </span>
                  )},
                  { key: "date",    header: "Submitted", render: (f) => (
                    <span className="text-xs text-gray-500">
                      {new Date(f.created_at).toLocaleDateString()}
                    </span>
                  )},
                ]}
                empty={
                  <p className="text-gray-500 text-sm">No feedback records found.</p>
                }
              />
            </Card>
          )
        )}

        {canSeeAll && pages > 1 && (
          <div className="flex items-center justify-center gap-3">
            <Button variant="secondary" size="sm" disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}>Previous</Button>
            <span className="text-gray-500 text-sm">Page {page} of {pages}</span>
            <Button variant="secondary" size="sm" disabled={page >= pages}
                    onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        )}

      </main>
    </>
  );
}
