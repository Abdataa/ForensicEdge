/**
 * src/services/imageService.ts
 * ──────────────────────────────
 * Forensic evidence image upload and management.
 *
 * Backend endpoints consumed
 * ───────────────────────────
 *   POST   /api/v1/images/upload         multipart/form-data → ImageUploadResponse
 *   GET    /api/v1/images                query params        → ImageListResponse
 *   GET    /api/v1/images/{id}                               → ImageResponse
 *   DELETE /api/v1/images/{id}                               → 204
 *
 * Evidence types
 * ───────────────
 *   "fingerprint" → stored under uploads/fingerprint/
 *                   processed by the fingerprint Siamese model
 *   "toolmark"    → stored under uploads/toolmark/
 *                   processed by the toolmark Siamese model
 *
 * Processing lifecycle (tracked by `status`)
 * ────────────────────────────────────────────
 *   uploaded → preprocessing → preprocessed → extracting → ready
 *   Any stage can transition to: failed
 *
 *   The frontend polls GET /images/{id} after upload until
 *   status === "ready" before allowing a comparison.
 */

import api from "./api";

// ── Types ────────────────────────────────────────────────────────────────────

export type EvidenceType =
  | "fingerprint"
  | "toolmark";

export type ImageStatus =
  | "uploaded"
  | "preprocessing"
  | "preprocessed"
  | "extracting"
  | "ready"
  | "failed";

/** Matches PreprocessedImageResponse */
export interface PreprocessedImageInfo {
  id:            number;
  enhanced_path: string;
  created_at:    string;
}

/** Matches FeatureSetResponse */
export interface FeatureSetInfo {
  id:               number;
  model_version_id: number | null;
  created_at:       string;
}

/**
 * Matches ImageUploadResponse
 * Returned immediately after POST /images/upload.
 * status will be "uploaded" — processing begins asynchronously.
 */
export interface ImageUploadResponse {
  id:                number;
  original_filename: string;
  evidence_type:     EvidenceType;
  file_size_bytes:   number;
  status:            ImageStatus;
  upload_date:       string;
  message:           string;
}

/**
 * Matches ImageResponse
 * Full image record returned by GET /images/{id}.
 * Includes preprocessing and embedding metadata once processing completes.
 * Note: backend uses alias user_id → uploader_id
 */
export interface ImageResponse {
  id:                 number;
  original_filename:  string;
  evidence_type:      EvidenceType;
  file_size_bytes:    number;
  status:             ImageStatus;
  upload_date:        string;
  uploader_id:        number;
  preprocessed_image: PreprocessedImageInfo | null;
  feature_set:        FeatureSetInfo        | null;
}

/** Matches ImageListResponse */
export interface ImageListResponse {
  total:  number;
  page:   number;
  limit:  number;
  images: ImageResponse[];
}

// ── Service ──────────────────────────────────────────────────────────────────

export const imageService = {

  /**
   * POST /api/v1/images/upload  (multipart/form-data)
   *
   * Sends the image file and evidence_type as form fields.
   * The backend validates, saves, preprocesses and embeds the image
   * automatically.  The returned status will initially be "uploaded".
   *
   * @param file          — File object from <input type="file">
   * @param evidenceType  — "fingerprint" | "toolmark"
   * @param onProgress    — optional callback receiving 0–100 upload %
   */
  async upload(
    file:          File,
    evidenceType:  EvidenceType,
    onProgress?:   (percent: number) => void,
  ): Promise<ImageUploadResponse> {
    const form = new FormData();
    form.append("file",          file);
    form.append("evidence_type", evidenceType);

    const { data } = await api.post<ImageUploadResponse>(
      "/images/upload",
      form,
      {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const pct = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(pct);
          }
        },
      },
    );
    return data;
  },

  /**
   * GET /api/v1/images/{id}
   * Returns full image metadata including current processing status.
   * Call this to poll until status === "ready".
   */
  async get(imageId: number): Promise<ImageResponse> {
    const { data } = await api.get<ImageResponse>(`/images/${imageId}`);
    return data;
  },

  /**
   * GET /api/v1/images
   * Returns a paginated list of images for the current user.
   *
   * @param params.evidence_type — filter to one type (optional)
   * @param params.page          — 1-based page number (default 1)
   * @param params.limit         — records per page (default 20)
   */
  async list(params?: {
    evidence_type?: EvidenceType;
    page?:          number;
    limit?:         number;
  }): Promise<ImageListResponse> {
    const { data } = await api.get<ImageListResponse>("/images", { params });
    return data;
  },

  /**
   * DELETE /api/v1/images/{id}
   * Permanently removes the image, its enhanced copy, and its embedding.
   */
  async delete(imageId: number): Promise<void> {
    await api.delete(`/images/${imageId}`);
  },

  /**
   * Polls GET /images/{id} at a fixed interval until status === "ready"
   * or status === "failed", or the timeout is exceeded.
   *
   * @param imageId    — ID returned by upload()
   * @param onStatus   — called on every poll with the current status
   * @param intervalMs — polling interval in ms (default 2 000)
   * @param timeoutMs  — give up after this many ms (default 120 000)
   *
   * @returns Promise that resolves with the final ImageResponse when ready,
   *          or rejects with an Error on failure / timeout.
   */
  pollUntilReady(
    imageId:     number,
    onStatus?:   (status: ImageStatus) => void,
    intervalMs = 2_000,
    timeoutMs  = 120_000,
  ): Promise<ImageResponse> {
    const deadline = Date.now() + timeoutMs;

    return new Promise<ImageResponse>((resolve, reject) => {
      const tick = async () => {
        try {
          const image = await imageService.get(imageId);
          onStatus?.(image.status);

          if (image.status === "ready") {
            resolve(image);
          } else if (image.status === "failed") {
            reject(
              new Error(
                `Processing failed for image ${imageId}. ` +
                `Please re-upload the image.`,
              )
            );
          } else if (Date.now() > deadline) {
            reject(
              new Error(
                `Processing timed out for image ${imageId} after ` +
                `${timeoutMs / 1000}s.`,
              )
            );
          } else {
            setTimeout(tick, intervalMs);
          }
        } catch (err) {
          reject(err);
        }
      };

      tick();
    });
  },
};
