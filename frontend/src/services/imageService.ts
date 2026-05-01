/**
 * src/services/imageService.ts
 * ─────────────────────────────
 * All forensic image + comparison API calls.
 *
 * Covers every backend endpoint:
 *   POST   /images/upload
 *   GET    /images                     (paginated, filterable)
 *   GET    /images/{id}
 *   DELETE /images/{id}
 *   GET    /images/{id}/comparison     (original vs enhanced)
 *
 *   POST   /compare                    (two-image similarity)
 *   GET    /compare                    (list past results)
 *   GET    /compare/{id}               (single result)
 *   POST   /compare/search             (single-image database search)  ← NEW
 */

import api from "./api";

// ─────────────────────────────────────────────────────────────────────────────
// Shared types
// ─────────────────────────────────────────────────────────────────────────────

export type EvidenceType = "fingerprint" | "toolmark";

export type ImageStatus =
  | "uploaded"
  | "preprocessing"
  | "preprocessed"
  | "extracting"
  | "ready"
  | "failed";

export type MatchStatus = "MATCH" | "POSSIBLE MATCH" | "NO MATCH";

// ── Image types ──────────────────────────────────────────────────────────────

export interface PreprocessedImageInfo {
  id:               number;
  enhanced_path:    string;
  processing_steps: Record<string, unknown>;
  created_at:       string;
}

export interface FeatureSetInfo {
  id:         number;
  created_at: string;
}

export interface ImageResponse {
  id:                number;
  original_filename: string;
  evidence_type:     EvidenceType;
  file_size_bytes:   number;
  status:            ImageStatus;
  upload_date:       string;
  preprocessed_image?: PreprocessedImageInfo | null;
  feature_set?:        FeatureSetInfo        | null;
}

export interface ImageUploadResponse {
  id:                number;
  original_filename: string;
  evidence_type:     EvidenceType;
  file_size_bytes:   number;
  status:            ImageStatus;
  upload_date:       string;
}

export interface ImageListResponse {
  total:  number;
  page:   number;
  limit:  number;
  images: ImageResponse[];
}

export interface ComparisonResponse {
  image_id: number;
  original: {
    filename:      string;
    data:          string;   // base64 data URI
    size_bytes:    number;
    evidence_type: EvidenceType;
  };
  enhanced: {
    filename:   string;
    data:       string;   // base64 data URI
    processing: Record<string, unknown>;
  } | null;
  status: ImageStatus;
}

// ── Similarity / comparison types ─────────────────────────────────────────────

export interface ImageSummary {
  id:                number;
  original_filename: string;
  evidence_type:     EvidenceType;
  status:            ImageStatus;
  upload_date:       string;
}

export interface SimilarityResponse {
  id:                    number;
  image_1:               ImageSummary;
  image_2:               ImageSummary;
  similarity_percentage: number;
  match_status:          MatchStatus;
  cosine_similarity:     number;
  euclidean_distance:    number;
  evidence_type:         EvidenceType;
  created_at:            string;
}

export interface SimilarityListResponse {
  total:   number;
  page:    number;
  limit:   number;
  results: SimilarityResponse[];
}

// Single-image database search result — one candidate per match
export interface SearchCandidate {
  image:                 ImageSummary;
  similarity_percentage: number;
  match_status:          MatchStatus;
  cosine_similarity:     number;
  euclidean_distance:    number;
}

export interface DatabaseSearchResponse {
  query_image:   ImageSummary;
  total_searched: number;
  candidates:    SearchCandidate[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Service
// ─────────────────────────────────────────────────────────────────────────────

export const imageService = {

  // ── Images ────────────────────────────────────────────────────────────────

  /** Upload a new forensic evidence image. */
  async upload(
    file:          File,
    evidenceType:  EvidenceType,
    onProgress?:   (pct: number) => void,
  ): Promise<ImageUploadResponse> {
    const form = new FormData();
    form.append("file",          file);
    form.append("evidence_type", evidenceType);

    const { data } = await api.post<ImageUploadResponse>("/images/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress
        ? (e) => {
            if (e.total) onProgress(Math.round((e.loaded / e.total) * 100));
          }
        : undefined,
    });
    return data;
  },

  /** List images with optional filter + pagination. */
  async list(params?: {
    evidence_type?: EvidenceType;
    page?:          number;
    limit?:         number;
  }): Promise<ImageListResponse> {
    const { data } = await api.get<ImageListResponse>("/images", { params });
    return data;
  },

  /** Get single image metadata. */
  async get(imageId: number): Promise<ImageResponse> {
    const { data } = await api.get<ImageResponse>(`/images/${imageId}`);
    return data;
  },

  /** Delete an image. */
  async delete(imageId: number): Promise<void> {
    await api.delete(`/images/${imageId}`);
  },

  /** Get original vs enhanced base64 images for side-by-side view. */
  async getComparison(imageId: number): Promise<ComparisonResponse> {
    const { data } = await api.get<ComparisonResponse>(`/images/${imageId}/comparison`);
    return data;
  },

  // ── Similarity comparisons ─────────────────────────────────────────────────

  /** Compare two images by ID. */
  async compare(imageAId: number, imageBId: number): Promise<SimilarityResponse> {
    const { data } = await api.post<SimilarityResponse>("/compare", {
      image_a_id: imageAId,
      image_b_id: imageBId,
    });
    return data;
  },

  /** List past comparison results, newest first. */
  async listResults(params?: {
    evidence_type?: EvidenceType;
    page?:          number;
    limit?:         number;
  }): Promise<SimilarityListResponse> {
    const { data } = await api.get<SimilarityListResponse>("/compare", { params });
    return data;
  },

  /** Get a single comparison result by ID. */
  async getResult(resultId: number): Promise<SimilarityResponse> {
    const { data } = await api.get<SimilarityResponse>(`/compare/${resultId}`);
    return data;
  },

  /**
   * Search the entire database for images similar to a single query image.
   * The backend ranks all stored embeddings of the same evidence type
   * and returns candidates ordered by similarity (highest first).
   *
   * POST /compare/search   { image_id, top_k?, threshold? }
   */
  async searchDatabase(params: {
    image_id:   number;
    top_k?:     number;    // how many candidates to return (default: 10)
    threshold?: number;    // minimum similarity % to include (default: 0)
  }): Promise<DatabaseSearchResponse> {
    const { data } = await api.post<DatabaseSearchResponse>("/compare/search", params);
    return data;
  },

  /** Poll GET /images/{id} until status reaches a terminal state. */
  async pollUntilReady(
    imageId:      number,
    onStatusChange?: (status: ImageStatus) => void,
    intervalMs = 2000,
    timeoutMs  = 120_000,
  ): Promise<ImageResponse> {
    const terminal = new Set<ImageStatus>(["ready", "failed", "preprocessed"]);
    const deadline = Date.now() + timeoutMs;

    return new Promise((resolve, reject) => {
      const tick = async () => {
        try {
          const img = await imageService.get(imageId);
          onStatusChange?.(img.status);
          if (terminal.has(img.status)) { resolve(img); return; }
          if (Date.now() >= deadline)   { reject(new Error("Polling timed out")); return; }
          setTimeout(tick, intervalMs);
        } catch (err) {
          reject(err);
        }
      };
      tick();
    });
  },
};