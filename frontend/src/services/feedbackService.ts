/**
 * src/services/feedbackService.ts
 * ─────────────────────────────────
 * Investigator feedback on similarity results.
 *
 * Backend endpoints consumed
 * ───────────────────────────
 *   POST /api/v1/feedback          body: FeedbackCreate  → FeedbackResponse
 *   GET  /api/v1/feedback          query params          → FeedbackListResponse
 *                                  (admin / ai_engineer only)
 *   GET  /api/v1/feedback/{id}                           → FeedbackResponse
 *                                  (admin / ai_engineer only)
 *   GET  /api/v1/feedback/export                         → dict[]
 *                                  (admin / ai_engineer only — for retraining)
 *
 * Human-in-the-loop cycle
 * ────────────────────────
 *   Investigator flags wrong result  →  feedback stored in DB
 *   AI engineer exports incorrect cases via /feedback/export
 *   retrain_from_feedback.py builds a hard-example dataset
 *   Model is retrained → better future predictions
 *
 * Access control
 * ───────────────
 *   submit()  — any authenticated active user (analyst, admin, ai_engineer)
 *   list()    — admin and ai_engineer only (HTTP 403 for analysts)
 *   get()     — admin and ai_engineer only
 *
 * One submission per result per user
 * ────────────────────────────────────
 *   The backend rejects duplicate submissions with HTTP 409 CONFLICT.
 *   The frontend should disable the feedback buttons once submitted.
 */

import api from "./api";

// ── Types ────────────────────────────────────────────────────────────────────

/**
 * Matches FeedbackResponse in backend/app/schemas/feedback_schema.py
 *
 * is_correct — true: investigator confirms the prediction was right
 *              false: investigator flags it as wrong (used for retraining)
 * comment    — optional explanation, especially useful when is_correct=false
 */
export interface FeedbackResponse {
  id:         number;
  result_id:  number;
  user_id:    number;
  is_correct: boolean;
  comment:    string | null;
  created_at: string;
}

/**
 * Matches FeedbackListResponse
 *
 * total_correct   — count of feedbacks where is_correct=true
 * total_incorrect — count of feedbacks where is_correct=false
 * Both are optional (null if the backend omits them).
 */
export interface FeedbackListResponse {
  total:           number;
  page:            number;
  limit:           number;
  feedback:        FeedbackResponse[];
  total_correct:   number | null;
  total_incorrect: number | null;
}

/**
 * Shape of records returned by GET /feedback/export
 * Used by the AI team to build a retraining dataset.
 */
export interface FeedbackExportRecord {
  feedback_id:           number;
  result_id:             number;
  image_id_1:            number;
  image_id_2:            number;
  similarity_percentage: number;
  match_status:          string;
  investigator_comment:  string | null;
}

// ── Service ──────────────────────────────────────────────────────────────────

export const feedbackService = {

  /**
   * POST /api/v1/feedback
   * Submits investigator feedback on a similarity result.
   *
   * @param resultId   — ID of the SimilarityResult being reviewed
   * @param isCorrect  — true: model was right | false: model was wrong
   * @param comment    — optional explanation (strongly recommended when
   *                     isCorrect=false to aid the retraining team)
   *
   * @throws AxiosError 404 if result not found or not accessible
   * @throws AxiosError 409 if feedback already submitted for this result
   */
  async submit(
    resultId:   number,
    isCorrect:  boolean,
    comment?:   string,
  ): Promise<FeedbackResponse> {
    const { data } = await api.post<FeedbackResponse>("/feedback", {
      result_id:  resultId,
      is_correct: isCorrect,
      comment:    comment ?? null,
    });
    return data;
  },

  /**
   * GET /api/v1/feedback
   * Returns paginated feedback records.
   * Requires admin or ai_engineer role (HTTP 403 otherwise).
   *
   * @param params.isCorrect — filter: true=correct, false=incorrect, undefined=all
   * @param params.page      — 1-based page number (default 1)
   * @param params.limit     — records per page (default 50)
   */
  async list(params?: {
    isCorrect?: boolean;
    page?:      number;
    limit?:     number;
  }): Promise<FeedbackListResponse> {
    // Map camelCase to the snake_case query param the backend expects
    const { data } = await api.get<FeedbackListResponse>("/feedback", {
      params: {
        is_correct: params?.isCorrect,
        page:       params?.page,
        limit:      params?.limit,
      },
    });
    return data;
  },

  /**
   * GET /api/v1/feedback/{id}
   * Returns a single feedback record.
   * Requires admin or ai_engineer role.
   */
  async get(feedbackId: number): Promise<FeedbackResponse> {
    const { data } = await api.get<FeedbackResponse>(
      `/feedback/${feedbackId}`,
    );
    return data;
  },

  /**
   * GET /api/v1/feedback/export
   * Exports all incorrect feedback cases as structured data for retraining.
   * Requires admin or ai_engineer role.
   *
   * The returned records are consumed by
   * ai_engine/training/retrain_from_feedback.py.
   */
  async exportIncorrect(): Promise<FeedbackExportRecord[]> {
    const { data } = await api.get<FeedbackExportRecord[]>(
      "/feedback/export",
    );
    return data;
  },
};