/**
 * src/pages/logs.tsx
 * ────────────────────
 * Activity history page — the current user's own audit trail.
 *
 * Endpoint: GET /api/v1/logs
 * Returns the current user's actions only (scoped server-side).
 * Admins can see all users' logs via GET /admin/logs (admin page).
 *
 * Features
 * ─────────
 *   Action type filter   — dropdown, resets page to 1 on change
 *   Colour-coded actions — each action type has a distinct colour
 *   Details column       — raw JSON details, truncated for display
 *   Pagination           — 30 per page
 */

import { useState, useEffect } from "react";
import Head from "next/head";
import { History } from "lucide-react";
import clsx from "clsx";
import { useAuth } from "../hooks/useAuth";

import AppLayout from "../components/layout/AppLayout";
import Card      from "../components/ui/Card";
import Button    from "../components/ui/Button";
import Spinner   from "../components/ui/Spinner";
import api       from "../services/api";





// ── Types ────────────────────────────────────────────────────────────────────

interface LogEntry {
  id:          number;
  action_type: string;
  details:     Record<string, unknown>;
  timestamp:   string;
}

interface LogsApiResponse {
  total: number;
  page:  number;
  limit: number;
  logs:  LogEntry[];
}

// ── Action colour map ─────────────────────────────────────────────────────────

const ACTION_COLOUR: Record<string, string> = {
  image_uploaded:       "text-blue-400",
  image_deleted:        "text-red-400",
  comparison_completed: "text-purple-400",
  report_generated:     "text-green-400",
  report_downloaded:    "text-green-300",
  feedback_submitted:   "text-yellow-400",
  user_login:           "text-gray-400",
  password_changed:     "text-orange-400",
  user_registered:      "text-cyan-400",
};

// ── Filter options ────────────────────────────────────────────────────────────

const FILTER_OPTIONS = [
  { value: "",                      label: "All actions" },
  { value: "image_uploaded",        label: "Image uploads" },
  { value: "image_deleted",         label: "Image deletions" },
  { value: "comparison_completed",  label: "Comparisons" },
  { value: "report_generated",      label: "Reports generated" },
  { value: "report_downloaded",     label: "Reports downloaded" },
  { value: "feedback_submitted",    label: "Feedback submitted" },
  { value: "user_login",            label: "Logins" },
];

const LIMIT = 30;

// ── Component ─────────────────────────────────────────────────────────────────

export default function LogsPage() {
  const [logs,    setLogs]    = useState<LogEntry[]>([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [filter,  setFilter]  = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get<LogsApiResponse>("/logs", {
        params: {
          page,
          limit:       LIMIT,
          action_type: filter || undefined,
        },
      })
      .then(({ data }) => {
        setLogs(data.logs);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, [page, filter]);

  const handleFilterChange = (value: string) => {
    setFilter(value);
    setPage(1);   // reset to page 1 on filter change
  };

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <>
      <Head><title>Activity History — ForensicEdge</title></Head>

      <AppLayout title="Activity History">

        {/* ── Header row ────────────────────────────────────────────────── */}
        <div  className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-white font-semibold text-lg">Your Activity</h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {loading ? "Loading…" : `${total} log entr${total !== 1 ? "ies" : "y"}`}
            </p>
          </div>

          {/* Action type filter */}
          <div className="space-y-1">
              <label htmlFor="action-type-filter" className="field-label">
                       Filter by action
                       </label>
          <select
            id = "action-type-filter"
            value={filter}
            onChange={(e) => handleFilterChange(e.target.value)}
            className="field text-sm w-auto min-w-[180px]"
          >
            {FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          </div>
        </div>

        {/* ── Content ───────────────────────────────────────────────────── */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>

        ) : logs.length === 0 ? (
          <Card className="text-center py-16 space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center
                            justify-center mx-auto">
              <History size={24} className="text-gray-600" />
            </div>
            <p className="text-gray-400 text-sm font-medium">
              {filter ? "No logs match this filter." : "No activity recorded yet."}
            </p>
            {filter && (
              <button
                onClick={() => handleFilterChange("")}
                className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
              >
                Clear filter
              </button>
            )}
          </Card>

        ) : (
          <Card padding="p-0">
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th className="w-12">#</th>
                    <th>Action</th>
                    <th>Details</th>
                    <th className="whitespace-nowrap">Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      {/* Row ID */}
                      <td className="text-gray-600 text-xs tabular-nums">
                        {log.id}
                      </td>

                      {/* Action type */}
                      <td>
                        <span
                          className={clsx(
                            "text-sm font-medium capitalize",
                            ACTION_COLOUR[log.action_type] ?? "text-gray-400",
                          )}
                        >
                          {log.action_type.replace(/_/g, " ")}
                        </span>
                      </td>

                      {/* Details — JSON truncated */}
                      <td>
                        <span
                          className="block truncate max-w-[320px] text-xs
                                     font-mono text-gray-500"
                          title={JSON.stringify(log.details)}
                        >
                          {JSON.stringify(log.details)}
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td className="text-gray-500 text-xs whitespace-nowrap">
                        {new Date(log.timestamp).toLocaleString(undefined, {
                          month:  "short",
                          day:    "numeric",
                          year:   "numeric",
                          hour:   "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* ── Pagination ────────────────────────────────────────────────── */}
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

      </AppLayout>
    </>
  );
}