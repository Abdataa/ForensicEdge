/**
 * src/components/forensic/ReportViewer.tsx
 * ──────────────────────────────────────────
 * Displays a single forensic report card with download button.
 * Used in a list on the /reports page.
 *
 * Layout (left → right)
 * ──────────────────────
 *   Blue FileText icon
 *   Report title + truncated notes + creation date
 *   Download PDF button (right-aligned)
 *
 * Download behaviour
 * ───────────────────
 *   Calls reportService.download() which fetches the PDF blob
 *   and triggers a browser file-save dialog.
 *   Shows a loading state on the button while the fetch is in progress.
 *   On error shows a toast notification.
 *
 * Props
 * ──────
 *   report — ReportResponse from reportService
 */

import { useState }  from "react";
import { FileText, Download, Calendar } from "lucide-react";
import toast         from "react-hot-toast";
import clsx          from "clsx";
import { ReportResponse, reportService } from "../../services/reportService";
import Button from "../ui/Button";

// ── Props ────────────────────────────────────────────────────────────────────

interface ReportViewerProps {
  report: ReportResponse;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ReportViewer({ report }: ReportViewerProps) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      // Triggers a browser file-save dialog — no new tab opened
      await reportService.download(
        report.id,
        `${report.title.replace(/\s+/g, "_")}.pdf`,
      );
      toast.success("Report downloaded.");
    } catch {
      toast.error("Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div
      className={clsx(
        "flex items-start justify-between gap-4",
        "bg-gray-900 border border-gray-800 rounded-xl p-4",
        "hover:border-gray-700 transition-colors",
      )}
    >

      {/* ── Left: icon + text ───────────────────────────────────────────── */}
      <div className="flex items-start gap-3 min-w-0">

        {/* Icon */}
        <div className="mt-0.5 p-2 bg-blue-950 rounded-lg shrink-0">
          <FileText size={16} className="text-blue-400" />
        </div>

        {/* Text */}
        <div className="min-w-0 space-y-1">

          {/* Title */}
          <p className="text-white text-sm font-medium truncate">
            {report.title}
          </p>

          {/* Notes snippet — only shown when notes exist */}
          {report.notes && (
            <p className="text-gray-500 text-xs line-clamp-1">
              {report.notes}
            </p>
          )}

          {/* Date row */}
          <div className="flex items-center gap-1.5 text-gray-600 text-xs">
            <Calendar size={11} aria-hidden="true" />
            <time dateTime={report.created_at}>
              {new Date(report.created_at).toLocaleDateString(undefined, {
                year:  "numeric",
                month: "short",
                day:   "numeric",
              })}
            </time>
            <span className="text-gray-700">·</span>
            <span>Result #{report.result_id}</span>
          </div>

        </div>
      </div>

      {/* ── Right: download button ───────────────────────────────────────── */}
      <Button
        variant="secondary"
        size="sm"
        icon={<Download size={13} />}
        loading={downloading}
        onClick={handleDownload}
        className="shrink-0"
      >
        {downloading ? "Downloading…" : "PDF"}
      </Button>

    </div>
  );
}