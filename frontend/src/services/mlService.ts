/**
 * src/services/mlService.ts
 * ──────────────────────────
 * Service layer for all ML / AI-engineer operations.
 *
 * Endpoints consumed
 * ───────────────────
 *   GET  /ml/datasets              → list datasets
 *   POST /ml/datasets              → upload new dataset
 *   GET  /ml/datasets/:id          → dataset detail
 *   DELETE /ml/datasets/:id        → delete dataset
 *
 *   GET  /ml/models                → list model versions
 *   GET  /ml/models/:id            → model version detail
 *   POST /ml/models/:id/activate   → set as active model
 *
 *   GET  /ml/jobs                  → list training jobs
 *   POST /ml/jobs                  → launch training job
 *   GET  /ml/jobs/:id              → job detail + live metrics
 *   POST /ml/jobs/:id/cancel       → cancel a running job
 *
 *   POST /ml/evaluate              → run evaluation on a dataset
 *   GET  /ml/evaluate/:id          → evaluation result
 *
 * All list endpoints accept { limit, page } query params.
 * All responses degrade gracefully — callers should use Promise.allSettled.
 */

import api from "./api";

// ─────────────────────────────────────────────────────────────────────────────
// Types (mirror backend Pydantic schemas)
// ─────────────────────────────────────────────────────────────────────────────

export interface MlDataset {
  id:            number;
  name:          string;
  evidence_type: string;           // "fingerprint" | "toolmark"
  image_count:   number;
  size_mb:       number;
  created_at:    string;
  status:        "ready" | "processing" | "error";
  description?:  string;
}

export interface MlDatasetListResponse {
  datasets: MlDataset[];
  total:    number;
  page:     number;
  limit:    number;
}

export interface MlModelVersion {
  id:              number;
  version:         string;          // "v2.4.1"
  evidence_type:   string;
  accuracy:        number;          // 0–100
  val_loss:        number;
  created_at:      string;
  is_active:       boolean;
  training_job_id: number | null;
  notes?:          string;
}

export interface MlModelListResponse {
  versions: MlModelVersion[];
  total:    number;
  page:     number;
  limit:    number;
}

export type TrainingJobStatus = "queued" | "running" | "completed" | "failed";

export interface MlTrainingJob {
  id:            number;
  name:          string;
  evidence_type: string;
  dataset_id:    number;
  dataset_name:  string;
  status:        TrainingJobStatus;
  progress_pct:  number;
  epochs_total:  number;
  epochs_done:   number;
  accuracy:      number | null;
  val_loss:      number | null;
  started_at:    string | null;
  finished_at:   string | null;
  created_by:    number;
  config?:       Record<string, unknown>;
}

export interface MlJobListResponse {
  jobs:  MlTrainingJob[];
  total: number;
  page:  number;
  limit: number;
}

export interface MlEvaluationResult {
  id:            number;
  model_id:      number;
  dataset_id:    number;
  accuracy:      number;
  precision:     number;
  recall:        number;
  f1_score:      number;
  created_at:    string;
  evidence_type: string;
}

export interface LaunchJobPayload {
  name:          string;
  evidence_type: string;
  dataset_id:    number;
  epochs?:       number;
  config?:       Record<string, unknown>;
}

export interface EvaluatePayload {
  model_id:   number;
  dataset_id: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Service methods
// ─────────────────────────────────────────────────────────────────────────────

export const mlService = {

  // ── Datasets ───────────────────────────────────────────────────────────────

  async listDatasets(params: { page?: number; limit?: number } = {}) {
    const { data } = await api.get<MlDatasetListResponse>("/ml/datasets", {
      params: { page: 1, limit: 20, ...params },
    });
    return data;
  },

  async getDataset(id: number) {
    const { data } = await api.get<MlDataset>(`/ml/datasets/${id}`);
    return data;
  },

  async uploadDataset(formData: FormData) {
    const { data } = await api.post<MlDataset>("/ml/datasets", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  async deleteDataset(id: number) {
    await api.delete(`/ml/datasets/${id}`);
  },

  // ── Model versions ─────────────────────────────────────────────────────────

  async listModels(params: { page?: number; limit?: number } = {}) {
    const { data } = await api.get<MlModelListResponse>("/ml/models", {
      params: { page: 1, limit: 20, ...params },
    });
    return data;
  },

  async getModel(id: number) {
    const { data } = await api.get<MlModelVersion>(`/ml/models/${id}`);
    return data;
  },

  async activateModel(id: number) {
    const { data } = await api.post<MlModelVersion>(`/ml/models/${id}/activate`);
    return data;
  },

  // ── Training jobs ──────────────────────────────────────────────────────────

  async listJobs(params: { page?: number; limit?: number } = {}) {
    const { data } = await api.get<MlJobListResponse>("/ml/jobs", {
      params: { page: 1, limit: 20, ...params },
    });
    return data;
  },

  async getJob(id: number) {
    const { data } = await api.get<MlTrainingJob>(`/ml/jobs/${id}`);
    return data;
  },

  async launchJob(payload: LaunchJobPayload) {
    const { data } = await api.post<MlTrainingJob>("/ml/jobs", payload);
    return data;
  },

  async cancelJob(id: number) {
    await api.post(`/ml/jobs/${id}/cancel`);
  },

  // ── Evaluation ─────────────────────────────────────────────────────────────

  async runEvaluation(payload: EvaluatePayload) {
    const { data } = await api.post<MlEvaluationResult>("/ml/evaluate", payload);
    return data;
  },

  async getEvaluation(id: number) {
    const { data } = await api.get<MlEvaluationResult>(`/ml/evaluate/${id}`);
    return data;
  },
};