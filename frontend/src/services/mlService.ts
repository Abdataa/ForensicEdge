/**
 * src/services/mlService.ts
 * ──────────────────────────
 * Service layer for all ML / AI-engineer operations.
 *
 * Endpoints consumed
 * ───────────────────
 *   GET    /ml/datasets              → list datasets (filterable)
 *   POST   /ml/datasets              → upload new dataset (multipart/form-data)
 *   GET    /ml/datasets/:id          → dataset detail
 *   DELETE /ml/datasets/:id          → delete dataset + files on disk
 *
 *   GET    /ml/models                → list model versions (filterable)
 *   GET    /ml/models/:id            → model version detail
 *   POST   /ml/models/:id/activate   → set as active inference model
 *
 *   GET    /ml/jobs                  → list training jobs (filterable)
 *   POST   /ml/jobs                  → launch training job
 *   GET    /ml/jobs/:id              → job detail + live progress
 *   POST   /ml/jobs/:id/cancel       → cancel queued/running job
 *
 *   GET    /ml/evaluate              → list evaluation results (filterable)
 *   POST   /ml/evaluate              → run model against a dataset
 *   GET    /ml/evaluate/:id          → single evaluation result detail
 *
 * All list methods accept strongly-typed filter params.
 * Unset / undefined / empty-string values are stripped before the
 * request is sent so the URL never contains "?key=".
 * All callers should use Promise.allSettled for graceful degradation.
 *
 * Changes from v1
 * ────────────────
 *   + listEvaluations()           — was missing entirely
 *   + MlEvaluationListResponse    — new type
 *   + ListEvaluationsParams       — new type
 *   + MlEvaluationResult.details  — fmr, fnmr, eer, confusion_matrix, note
 *   + ListDatasetsParams          — typed filter object (was plain Record)
 *   + ListJobsParams              — typed, includes status filter
 *   + ListModelsParams            — typed
 *   + clean()                     — strips falsy params before every request
 *   + full JSDoc on every method
 *   + explicit return types on every method
 */

import api from "./api";

// ─────────────────────────────────────────────────────────────────────────────
// Shared literals
// ─────────────────────────────────────────────────────────────────────────────

export type EvidenceType      = "fingerprint" | "toolmark";
export type DatasetStatus     = "processing" | "ready" | "error";
export type TrainingJobStatus = "queued" | "running" | "completed" | "failed";

// ─────────────────────────────────────────────────────────────────────────────
// Dataset types
// ─────────────────────────────────────────────────────────────────────────────

export interface MlDataset {
  id:             number;
  name:           string;
  description?:   string;
  evidence_type:  EvidenceType | string;
  image_count:    number;
  size_mb:        number;
  status:         DatasetStatus;
  error_message?: string;
  file_path?:     string;
  created_by?:    number | null;
  created_at:     string;
  updated_at:     string;
}

export interface MlDatasetListResponse {
  datasets: MlDataset[];
  total:    number;
  page:     number;
  limit:    number;
}

export interface ListDatasetsParams {
  page?:          number;
  limit?:         number;
  evidence_type?: EvidenceType | string;
  status?:        DatasetStatus | string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Model version types
// ─────────────────────────────────────────────────────────────────────────────

export interface MlModelVersion {
  id:              number;
  version:         string;                  // e.g. "v1.3"
  evidence_type:   EvidenceType | string;
  accuracy:        number;                  // 0 – 100
  val_loss:        number;
  /**
   * Full metric dict from the training run.
   * May include: precision, recall, f1_score, fmr, fnmr, eer,
   * confusion_matrix, and any custom keys emitted by the trainer.
   */
  metrics?:        Record<string, unknown>;
  notes?:          string;
  is_active:       boolean;
  training_job_id: number | null;
  created_by?:     number | null;
  created_at:      string;
}

export interface MlModelListResponse {
  versions: MlModelVersion[];
  total:    number;
  page:     number;
  limit:    number;
}

export interface ListModelsParams {
  page?:          number;
  limit?:         number;
  evidence_type?: EvidenceType | string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Training job types
// ─────────────────────────────────────────────────────────────────────────────

export interface MlTrainingJob {
  id:             number;
  name:           string;
  evidence_type:  EvidenceType | string;
  dataset_id:     number | null;
  /** Denormalised by the backend so the dashboard avoids a second request. */
  dataset_name:   string;
  status:         TrainingJobStatus;
  progress_pct:   number;        // 0 – 100
  epochs_total:   number;
  epochs_done:    number;
  accuracy:       number | null; // null while running / not yet computed
  val_loss:       number | null;
  error_message?: string;
  /** Hyperparameter dict passed to the training engine. */
  config?:        Record<string, unknown>;
  created_by?:    number | null;
  started_at:     string | null;
  finished_at:    string | null;
  created_at:     string;
}

export interface MlJobListResponse {
  jobs:  MlTrainingJob[];
  total: number;
  page:  number;
  limit: number;
}

export interface ListJobsParams {
  page?:          number;
  limit?:         number;
  evidence_type?: EvidenceType | string;
  /** Filter by job lifecycle status. */
  status?:        TrainingJobStatus | string;
}

export interface LaunchJobPayload {
  name:          string;
  evidence_type: EvidenceType | string;
  dataset_id:    number;
  epochs?:       number;
  /** Hyperparameters forwarded verbatim to the training engine. */
  config?:       Record<string, unknown>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Evaluation types
// ─────────────────────────────────────────────────────────────────────────────

/**
 * A single evaluation run result.
 *
 * Core metrics (accuracy / precision / recall / f1_score) are always 0–100.
 *
 * `details` carries the full evaluation engine output.  Known keys:
 *   fmr              — False Match Rate (0.0 – 1.0)
 *   fnmr             — False Non-Match Rate (0.0 – 1.0)
 *   eer              — Equal Error Rate (0.0 – 1.0)
 *   confusion_matrix — [[TP,FP],[FN,TN]]
 *   note             — string if evaluation engine is not yet integrated
 *
 * Pages multiply fmr/fnmr/eer by 100 before passing to MetricBar.
 *
 */
export interface MlEvaluationDetails {
  fmr?: number;   // 0–1
  fnmr?: number;  // 0–1
  eer?: number;   // 0–1
  confusion_matrix?: [[number, number], [number, number]];
  note?: string;

  // allow future fields
  [key: string]: unknown;
}


export interface MlEvaluationResult {
  id:            number;
  model_id:      number;
  dataset_id:    number | null;
  evidence_type: EvidenceType | string;
  accuracy:      number;   // 0 – 100
  precision:     number;   // 0 – 100
  recall:        number;   // 0 – 100
  f1_score:      number;   // 0 – 100
  details?: MlEvaluationDetails;
  created_by?:   number | null;
  created_at:    string;
}

export interface MlEvaluationListResponse {
  evaluations: MlEvaluationResult[];
  total:       number;
  page:        number;
  limit:       number;
}

export interface ListEvaluationsParams {
  page?:          number;
  limit?:         number;
  model_id?:      number;
  evidence_type?: EvidenceType | string;
}

export interface EvaluatePayload {
  model_id:   number;
  dataset_id: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal helper
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Strip undefined / null / empty-string values from a params object before
 * passing it to Axios so the URL never contains bare "?key=" entries.
 */
function clean<T extends Record<string, unknown>>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, v]) => v !== undefined && v !== null && v !== ""
    )
  ) as Partial<T>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Service
// ─────────────────────────────────────────────────────────────────────────────

export const mlService = {

  // ── Datasets ───────────────────────────────────────────────────────────────

  /**
   * List datasets with optional filtering by evidence type and/or status.
   *
   * @example
   * // All ready fingerprint datasets
   * mlService.listDatasets({ evidence_type: "fingerprint", status: "ready" })
   */
  async listDatasets(
    params: ListDatasetsParams = {}
  ): Promise<MlDatasetListResponse> {
    const { data } = await api.get<MlDatasetListResponse>("/ml/datasets", {
      params: clean({ page: 1, limit: 20, ...params } as Record<string, unknown>),
    });
    return data;
  },

  /** Get a single dataset by ID. */
  async getDataset(id: number): Promise<MlDataset> {
    const { data } = await api.get<MlDataset>(`/ml/datasets/${id}`);
    return data;
  },

  /**
   * Upload a new dataset as a zip archive.
   *
   * The caller must build the FormData:
   *   formData.append("name",          "FVC2000-DB1")
   *   formData.append("evidence_type", "fingerprint")
   *   formData.append("description",   "optional")
   *   formData.append("file",          zipFile)
   *
   * Returns 202 Accepted — the record is created with status="processing".
   * Poll getDataset() or listDatasets() until status transitions to "ready".
   */
  async uploadDataset(formData: FormData): Promise<MlDataset> {
    const { data } = await api.post<MlDataset>("/ml/datasets", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  /**
   * Permanently delete a dataset and remove its files from disk.
   * Training jobs that referenced this dataset are preserved (FK → NULL).
   */
  async deleteDataset(id: number): Promise<void> {
    await api.delete(`/ml/datasets/${id}`);
  },

  // ── Model versions ─────────────────────────────────────────────────────────

  /**
   * List model versions ordered newest-first.
   * The currently active version for each evidence_type has is_active=true.
   *
   * @example
   * mlService.listModels({ evidence_type: "toolmark", limit: 10 })
   */
  async listModels(
    params: ListModelsParams = {}
  ): Promise<MlModelListResponse> {
    const { data } = await api.get<MlModelListResponse>("/ml/models", {
      params: clean({ page: 1, limit: 20, ...params } as Record<string, unknown>),
    });
    return data;
  },

  /** Get full details for a model version, including the complete metrics dict. */
  async getModel(id: number): Promise<MlModelVersion> {
    const { data } = await api.get<MlModelVersion>(`/ml/models/${id}`);
    return data;
  },

  /**
   * Activate a model version for live inference.
   *
   * - All other versions of the same evidence_type are deactivated atomically.
   * - The in-memory inference engine is hot-swapped immediately.
   * - Idempotent: activating an already-active model returns it unchanged.
   */
  async activateModel(id: number): Promise<MlModelVersion> {
    const { data } = await api.post<MlModelVersion>(`/ml/models/${id}/activate`);
    return data;
  },

  // ── Training jobs ──────────────────────────────────────────────────────────

  /**
   * List training jobs with optional filtering.
   *
   * @example
   * // All running jobs
   * mlService.listJobs({ status: "running" })
   *
   * @example
   * // All fingerprint jobs, newest 50
   * mlService.listJobs({ evidence_type: "fingerprint", limit: 50 })
   */
  async listJobs(
    params: ListJobsParams = {}
  ): Promise<MlJobListResponse> {
    const { data } = await api.get<MlJobListResponse>("/ml/jobs", {
      params: clean({ page: 1, limit: 20, ...params } as Record<string, unknown>),
    });
    return data;
  },

  /**
   * Get a single job by ID.
   * Poll this every 3 s while status === "running" to show live progress.
   */
  async getJob(id: number): Promise<MlTrainingJob> {
    const { data } = await api.get<MlTrainingJob>(`/ml/jobs/${id}`);
    return data;
  },

  /**
   * Launch a new training run.
   * Returns 202 Accepted — the job is queued immediately.
   * Poll getJob() or listJobs({ status: "running" }) to track progress.
   *
   * @example
   * mlService.launchJob({
   *   name:          "fp-resnet-v3",
   *   evidence_type: "fingerprint",
   *   dataset_id:    12,
   *   epochs:        100,
   *   config:        { lr: 0.001, batch_size: 32 },
   * })
   */
  async launchJob(payload: LaunchJobPayload): Promise<MlTrainingJob> {
    const { data } = await api.post<MlTrainingJob>("/ml/jobs", payload);
    return data;
  },

  /**
   * Cancel a queued or running job.
   * The job transitions to status="failed" with error_message="Cancelled by admin."
   * Already completed or failed jobs cannot be cancelled (backend returns 409).
   */
  async cancelJob(id: number): Promise<void> {
    await api.post(`/ml/jobs/${id}/cancel`);
  },

  // ── Evaluation ─────────────────────────────────────────────────────────────

  /**
   * List past evaluation results with optional filtering.
   *
   * @example
   * // All evaluations for model #3
   * mlService.listEvaluations({ model_id: 3 })
   *
   * @example
   * // Latest 20 fingerprint evaluations
   * mlService.listEvaluations({ evidence_type: "fingerprint", limit: 20 })
   */
  async listEvaluations(
    params: ListEvaluationsParams = {}
  ): Promise<MlEvaluationListResponse> {
    const { data } = await api.get<MlEvaluationListResponse>("/ml/evaluate", {
      params: clean({ page: 1, limit: 20, ...params } as Record<string, unknown>),
    });
    return data;
  },

  /**
   * Run a model against an evaluation dataset and persist the results.
   *
   * - The model and dataset must share the same evidence_type.
   * - The dataset must be in status="ready".
   * - Returns accuracy, precision, recall, f1_score, and a details dict
   *   containing fmr, fnmr, eer, confusion_matrix once the eval engine
   *   is integrated in ml_service.py.
   *
   * @example
   * mlService.runEvaluation({ model_id: 5, dataset_id: 2 })
   */
  async runEvaluation(payload: EvaluatePayload): Promise<MlEvaluationResult> {
    const { data } = await api.post<MlEvaluationResult>("/ml/evaluate", payload);
    return data;
  },

  /** Get a single evaluation result by ID. */
  async getEvaluation(id: number): Promise<MlEvaluationResult> {
    const { data } = await api.get<MlEvaluationResult>(`/ml/evaluate/${id}`);
    return data;
  },
};