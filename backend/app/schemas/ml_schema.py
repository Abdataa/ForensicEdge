"""
backend/app/schemas/ml_schema.py
─────────────────────────────────
Pydantic v2 request / response schemas for the ML-Ops subsystem.

Naming convention (consistent with the rest of the app)
────────────────────────────────────────────────────────
    <Entity>Create   — POST request body
    <Entity>Update   — PATCH request body (all fields Optional)
    <Entity>Response — single object returned from API
    <Entity>ListResponse — paginated list wrapper

Evidence type literals
──────────────────────
    "fingerprint" | "toolmark"
    Validated at schema level so the DB never gets arbitrary strings.
"""

from __future__ import annotations

from datetime import datetime
from typing   import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# Allowed evidence types — single source of truth
EvidenceType = Literal["fingerprint", "toolmark"]

# Allowed status values per entity
DatasetStatus = Literal["processing", "ready", "error"]
JobStatus     = Literal["queued", "running", "completed", "failed"]


# ─────────────────────────────────────────────────────────────────────────────
# Dataset schemas
# ─────────────────────────────────────────────────────────────────────────────

class DatasetCreate(BaseModel):
    """
    Sent as multipart/form-data — the zip file is a separate UploadFile param.
    These are the form fields that accompany it.
    """
    name:          str         = Field(..., min_length=2, max_length=255)
    evidence_type: EvidenceType
    description:   Optional[str] = Field(None, max_length=1000)


class DatasetResponse(BaseModel):
    id:            int
    name:          str
    evidence_type: str
    description:   Optional[str]
    image_count:   int
    size_mb:       float
    status:        str
    error_message: Optional[str]
    created_by:    Optional[int]
    created_at:    datetime
    updated_at:    datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]
    total:    int
    page:     int
    limit:    int


# ─────────────────────────────────────────────────────────────────────────────
# Model version schemas
# ─────────────────────────────────────────────────────────────────────────────

class ModelVersionResponse(BaseModel):
    id:              int
    version:         str
    evidence_type:   str
    accuracy:        float
    val_loss:        float
    metrics:         Optional[Dict[str, Any]]
    notes:           Optional[str]
    is_active:       bool
    training_job_id: Optional[int]
    created_by:      Optional[int]
    created_at:      datetime

    model_config = {"from_attributes": True}


class ModelVersionListResponse(BaseModel):
    versions: List[ModelVersionResponse]
    total:    int
    page:     int
    limit:    int


# ─────────────────────────────────────────────────────────────────────────────
# Training job schemas
# ─────────────────────────────────────────────────────────────────────────────

class TrainingJobCreate(BaseModel):
    """
    Body for POST /ml/jobs — launch a new training run.
    """
    name:          str          = Field(..., min_length=2, max_length=255)
    evidence_type: EvidenceType
    dataset_id:    int          = Field(..., gt=0)
    epochs:        int          = Field(50,  ge=1, le=1000)
    config:        Optional[Dict[str, Any]] = None   # hyperparameters

    @field_validator("config")
    @classmethod
    def config_must_be_serialisable(cls, v: Optional[Dict]) -> Optional[Dict]:
        """Reject config values that can't round-trip through JSON."""
        if v is None:
            return v
        import json
        try:
            json.dumps(v)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"config must be JSON-serialisable: {exc}") from exc
        return v


class TrainingJobProgressUpdate(BaseModel):
    """
    PATCH /ml/jobs/:id/progress — called by the training worker.
    All fields optional so partial updates are allowed.
    """
    progress_pct: Optional[int]   = Field(None, ge=0, le=100)
    epochs_done:  Optional[int]   = Field(None, ge=0)
    accuracy:     Optional[float] = Field(None, ge=0.0, le=100.0)
    val_loss:     Optional[float] = Field(None, ge=0.0)
    status:       Optional[JobStatus] = None
    error_message: Optional[str]  = None


class TrainingJobResponse(BaseModel):
    id:            int
    name:          str
    evidence_type: str
    dataset_id:    Optional[int]
    dataset_name:  str           # denormalised for the dashboard
    status:        str
    progress_pct:  int
    epochs_total:  int
    epochs_done:   int
    accuracy:      Optional[float]
    val_loss:      Optional[float]
    error_message: Optional[str]
    config:        Optional[Dict[str, Any]]
    created_by:    Optional[int]
    started_at:    Optional[datetime]
    finished_at:   Optional[datetime]
    created_at:    datetime

    model_config = {"from_attributes": True}


class TrainingJobListResponse(BaseModel):
    jobs:  List[TrainingJobResponse]
    total: int
    page:  int
    limit: int


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation schemas
# ─────────────────────────────────────────────────────────────────────────────

class EvaluationCreate(BaseModel):
    """
    Body for POST /ml/evaluate — run a model against a dataset.
    """
    model_id:   int = Field(..., gt=0)
    dataset_id: int = Field(..., gt=0)

    @model_validator(mode="after")
    def ids_must_differ(self) -> "EvaluationCreate":
        # Nothing to validate here structurally, but keep hook for future rules.
        return self


class EvaluationResponse(BaseModel):
    id:            int
    model_id:      int
    dataset_id:    Optional[int]
    evidence_type: str
    accuracy:      float
    precision:     float
    recall:        float
    f1_score:      float
    details:       Optional[Dict[str, Any]]
    created_by:    Optional[int]
    created_at:    datetime

    model_config = {"from_attributes": True}


class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]
    total:       int
    page:        int
    limit:       int