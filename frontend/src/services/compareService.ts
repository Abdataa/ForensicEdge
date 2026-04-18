/**
 * src/services/compareService.ts
 * ────────────────────────────────
 * Forensic image similarity comparison.
 *
 * Backend endpoints consumed
 * ───────────────────────────
 *   POST /api/v1/compare            body: CompareRequest → SimilarityResponse
 *   GET  /api/v1/compare            query params         → SimilarityListResponse
 *   GET  /api/v1/compare/{id}                            → SimilarityResponse
 *
 * Cross-type guard (enforced server-side)
 * ────────────────────────────────────────
 *   Comparing a fingerprint image against a toolmark image is
 *   scientifically invalid.  The backend rejects such requests with
 *   HTTP 400.  The frontend should also prevent this via
 *   EvidenceTypeSelector, but the server guard is authoritative.
 *
 * Metric interpretation
 * ──────────────────────
 *   similarity_percentage — 0–100  (higher = more similar, investigator-facing)
 *   cosine_similarity     — -1..1  (raw embedding dot product after L2-norm)
 *   euclidean_distance    — 0..2   (L2 distance between unit-norm embeddings)
 *   match_status          — "MATCH" | "POSSIBLE MATCH" | "NO MATCH"
 *
 * Default thresholds (configurable in backend .env)
 *   similarity_percentage ≥ 85 → MATCH
 *   similarity_percentage ≥ 60 → POSSIBLE MATCH
 *   otherwise              → NO MATCH
 */

import api from "./api";
import { EvidenceType } from "./imageService";

// ── Types ────────────────────────────────────────────────────────────────────

export type MatchStatus =
  | "MATCH"
  | "POSSIBLE MATCH"
  | "NO MATCH";

/**
 * Compact image info embedded inside SimilarityResponse.
 * Matches ImageSummary in backend/app/schemas/similarity_schema.py
 */
export interface ImageSummary {
  id:                number;
  original_filename: string;
  evidence_type:     EvidenceType;
  upload_date:       string;
}

/**
 * Full similarity result.
 * Matches SimilarityResponse in backend/app/schemas/similarity_schema.py
 *
 * image_1 — the query image (first argument to compare())
 * image_2 — the reference image (second argument)
 * requested_by_id — user ID who requested the comparison (or null)
 */
export interface SimilarityResponse {
  id:                    number;
  similarity_percentage: number;       // [0, 100]
  cosine_similarity:     number;       // [-1, 1]
  euclidean_distance:    number;       // [0,  2]
  match_status:          MatchStatus;
  created_at:            string;
  requested_by_id:       number | null;
  image_1:               ImageSummary | null;
  image_2:               ImageSummary | null;
}

/** Matches SimilarityListResponse */
export interface SimilarityListResponse {
  total:   number;
  page:    number;
  limit:   number;
  results: SimilarityResponse[];
}

// ── Service ──────────────────────────────────────────────────────────────────

export const compareService = {

  /**
   * POST /api/v1/compare
   * Runs forensic similarity analysis between two uploaded images.
   *
   * Prerequisites (enforced by backend):
   *   - Both images must belong to the current user (or user is admin)
   *   - Both images must have status === "ready"
   *   - Both images must be the SAME evidence type
   *   - image_id_1 must not equal image_id_2
   *
   * @param imageId1 — ID of the query evidence image
   * @param imageId2 — ID of the reference evidence image
   */
  async compare(
    imageId1: number,
    imageId2: number,
  ): Promise<SimilarityResponse> {
    const { data } = await api.post<SimilarityResponse>("/compare", {
      image_id_1: imageId1,
      image_id_2: imageId2,
    });
    return data;
  },

  /**
   * GET /api/v1/compare/{id}
   * Retrieves a single past comparison result by its ID.
   * Used to reload a result from the history page.
   */
  async get(resultId: number): Promise<SimilarityResponse> {
    const { data } = await api.get<SimilarityResponse>(
      `/compare/${resultId}`
    );
    return data;
  },

  /**
   * GET /api/v1/compare
   * Returns paginated comparison history for the current user.
   *
   * @param params.evidence_type — filter to "fingerprint" | "toolmark" (optional)
   * @param params.page          — 1-based page (default 1)
   * @param params.limit         — records per page (default 20)
   */
  async list(params?: {
    evidence_type?: EvidenceType;
    page?:          number;
    limit?:         number;
  }): Promise<SimilarityListResponse> {
    const { data } = await api.get<SimilarityListResponse>(
      "/compare",
      { params },
    );
    return data;
  },
};