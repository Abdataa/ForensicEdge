/**
 * src/services/reportService.ts
 * ──────────────────────────────
 * Forensic PDF report generation and download.
 *
 * Backend endpoints consumed
 * ───────────────────────────
 *   POST /api/v1/reports                 body: ReportCreate  → ReportResponse
 *   GET  /api/v1/reports                 query params        → ReportListResponse
 *   GET  /api/v1/reports/{id}                                → ReportResponse
 *   GET  /api/v1/reports/{id}/download                       → PDF blob (binary)
 *
 * One report per similarity result
 * ──────────────────────────────────
 * The backend enforces a unique constraint: only one report can exist
 * per similarity result.  A second attempt returns HTTP 409 CONFLICT.
 * The frontend should check for an existing report before calling generate().
 *
 * Download behaviour
 * ───────────────────
 * download() fetches the PDF as a binary blob and triggers a browser
 * file-save dialog using a temporary <a> element.  No new browser tab
 * is opened.  This works across all modern browsers.
 */

import api from "./api";
import { SimilarityResponse } from "./compareService";

// ── Types ────────────────────────────────────────────────────────────────────

/**
 * Matches ReportResponse in backend/app/schemas/report_schema.py
 *
 * pdf_path  — server-side filesystem path (not directly accessible by
 *             the browser — use download() to fetch the file)
 * similarity_result — optionally embedded for dashboard display
 */
export interface ReportResponse {
  id:               number;
  title:            string;
  notes:            string | null;
  pdf_path:         string;
  created_at:       string;
  user_id:          number;
  result_id:        number;
  similarity_result?: SimilarityResponse | null;
}

/** Matches ReportListResponse */
export interface ReportListResponse {
  total:   number;
  page:    number;
  limit:   number;
  reports: ReportResponse[];
}

// ── Service ──────────────────────────────────────────────────────────────────

export const reportService = {

  /**
   * POST /api/v1/reports
   * Generates a forensic PDF report for a completed similarity result.
   *
   * The PDF contains:
   *   - Similarity percentage and match status (colour-coded)
   *   - All three metrics (similarity%, cosine, euclidean)
   *   - Both evidence image filenames
   *   - Evidence type (fingerprint | toolmark)
   *   - Analyst notes (if provided)
   *   - Professional disclaimer for courtroom use
   *
   * @param resultId — ID of the SimilarityResult to summarise
   * @param title    — optional report title (default: "Forensic Analysis Report")
   * @param notes    — optional analyst observations to embed in the PDF
   *
   * @throws AxiosError 409 if a report already exists for this result
   */
  async generate(
    resultId: number,
    title?:   string,
    notes?:   string,
  ): Promise<ReportResponse> {
    const { data } = await api.post<ReportResponse>("/reports", {
      result_id: resultId,
      title:     title ?? "Forensic Analysis Report",
      notes:     notes ?? null,
    });
    return data;
  },

  /**
   * GET /api/v1/reports/{id}
   * Returns metadata for a single report.
   * Does NOT return the PDF bytes — use download() for that.
   */
  async get(reportId: number): Promise<ReportResponse> {
    const { data } = await api.get<ReportResponse>(`/reports/${reportId}`);
    return data;
  },

  /**
   * GET /api/v1/reports
   * Returns a paginated list of reports for the current user.
   *
   * @param params.page  — 1-based page number (default 1)
   * @param params.limit — records per page (default 20)
   */
  async list(params?: {
    page?:  number;
    limit?: number;
  }): Promise<ReportListResponse> {
    const { data } = await api.get<ReportListResponse>("/reports", { params });
    return data;
  },

  /**
   * GET /api/v1/reports/{id}/download
   * Fetches the PDF as a binary blob and triggers a browser file-save.
   *
   * Implementation:
   *   1. Fetches with responseType: "blob"
   *   2. Creates a temporary object URL
   *   3. Clicks a hidden <a download> element
   *   4. Revokes the URL to free memory
   *
   * @param reportId — ID of the report to download
   * @param filename — optional filename for the saved file
   *                   (default: "report_{id}.pdf")
   */
  async download(reportId: number, filename?: string): Promise<void> {
    const response = await api.get(
      `/reports/${reportId}/download`,
      { responseType: "blob" },
    );

    const blob     = new Blob([response.data], { type: "application/pdf" });
    const url      = URL.createObjectURL(blob);
    const anchor   = document.createElement("a");

    anchor.href     = url;
    anchor.download = filename ?? `report_${reportId}.pdf`;

    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);

    // Release the blob URL — browser holds a reference until revoked
    URL.revokeObjectURL(url);
  },
};