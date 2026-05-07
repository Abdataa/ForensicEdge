"""
backend/app/api/routes_ml.py
─────────────────────────────
ML-Ops endpoints — accessible to ai_engineer and admin roles.

Endpoints
─────────
    Datasets
    ─────────
    GET    /api/v1/ml/datasets              — list datasets (paginated, filterable)
    POST   /api/v1/ml/datasets              — upload new dataset (multipart/form-data)
    GET    /api/v1/ml/datasets/{id}         — dataset detail
    DELETE /api/v1/ml/datasets/{id}         — delete dataset + files on disk

    Model versions
    ──────────────
    GET    /api/v1/ml/models                — list versions (paginated, filterable)
    GET    /api/v1/ml/models/{id}           — model version detail
    POST   /api/v1/ml/models/{id}/activate  — set as active inference model

    Training jobs
    ─────────────
    GET    /api/v1/ml/jobs                  — list jobs (paginated, filterable)
    POST   /api/v1/ml/jobs                  — launch new training run
    GET    /api/v1/ml/jobs/{id}             — job detail + live progress
    POST   /api/v1/ml/jobs/{id}/cancel      — cancel queued or running job
    PATCH  /api/v1/ml/jobs/{id}/progress    — internal: worker progress update

    Evaluation
    ──────────
    GET    /api/v1/ml/evaluate              — list evaluation results
    POST   /api/v1/ml/evaluate              — run model against a dataset
    GET    /api/v1/ml/evaluate/{id}         — evaluation detail

Access control
──────────────
    MlUser dependency  — ai_engineer OR admin (see app/core/dependencies.py)
    Progress PATCH     — additionally accepts an internal worker API key

All list endpoints support ?page=&limit=&evidence_type= query params.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database    import get_db
#from app.core.dependencies import MlUser   #
from app.core.dependencies import AIOrAdminUser
from app.schemas.ml_schema import (
    DatasetCreate,
    DatasetListResponse,
    DatasetResponse,
    EvaluationCreate,
    EvaluationListResponse,
    EvaluationResponse,
    ModelVersionListResponse,
    ModelVersionResponse,
    TrainingJobCreate,
    TrainingJobListResponse,
    TrainingJobProgressUpdate,
    TrainingJobResponse,
)
from app.services           import ml_service
from app.services.log_service import create_log

router = APIRouter(prefix="/ml", tags=["ML Operations"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper — build TrainingJobResponse (adds denormalised dataset_name)
# ─────────────────────────────────────────────────────────────────────────────

async def _job_response(job, db: AsyncSession) -> TrainingJobResponse:
    """Resolve dataset_name from the FK so the frontend doesn't need a join."""
    dataset_name = "—"
    if job.dataset_id is not None:
        try:
            ds = await ml_service.get_dataset_or_404(db, job.dataset_id)
            dataset_name = ds.name
        except Exception:
            pass

    data = TrainingJobResponse.model_validate(job)
    # Override the computed field (model_validate uses from_attributes)
    return data.model_copy(update={"dataset_name": dataset_name})


# ─────────────────────────────────────────────────────────────────────────────
# Datasets
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/datasets",
    response_model = DatasetListResponse,
    summary        = "List training / evaluation datasets",
)
async def list_datasets(
    current_user:  AIOrAdminUser,
    page:          int           = Query(1,  ge=1),
    limit:         int           = Query(20, ge=1, le=100),
    evidence_type: Optional[str] = Query(None, description="fingerprint | toolmark"),
    status_filter: Optional[str] = Query(None, alias="status",
                                         description="processing | ready | error"),
    db:            AsyncSession  = Depends(get_db),
):
    """
    Returns a paginated list of datasets.

    Filterable by:
    - **evidence_type**: fingerprint | toolmark
    - **status**: processing | ready | error
    """
    datasets, total = await ml_service.list_datasets(
        db            = db,
        page          = page,
        limit         = limit,
        evidence_type = evidence_type,
        status_filter = status_filter,
    )
    return DatasetListResponse(
        datasets = [DatasetResponse.model_validate(d) for d in datasets],
        total    = total,
        page     = page,
        limit    = limit,
    )


@router.post(
    "/datasets",
    response_model = DatasetResponse,
    status_code    = status.HTTP_202_ACCEPTED,
    summary        = "Upload a new labelled dataset (zip archive)",
)
async def upload_dataset(
    request:       Request,
    current_user:  AIOrAdminUser,
    name:          str          = Form(..., min_length=2, max_length=255),
    evidence_type: str          = Form(...),
    description:   Optional[str] = Form(None),
    file:          UploadFile   = File(..., description="Zip archive of labelled images"),
    db:            AsyncSession = Depends(get_db),
):
    """
    Upload a dataset as a zip archive.

    - The zip may contain sub-directories; all image files inside are counted.
    - Accepted image formats: jpg, jpeg, png, bmp, tiff.
    - The record is created immediately with `status=processing`; unpacking
      happens in the background. Poll the GET endpoint to track progress.
    - Returns 202 Accepted — the dataset is not yet usable until
      `status=ready`.
    """
    payload = DatasetCreate(
        name          = name,
        evidence_type = evidence_type,  # type: ignore[arg-type]
        description   = description,
    )
    dataset = await ml_service.create_dataset(
        db      = db,
        payload = payload,
        file    = file,
        user_id = current_user.id,
    )

    await create_log(
        db          = db,
        action_type = "dataset_uploaded",
        user_id     = current_user.id,
        details     = {
            "dataset_id":    dataset.id,
            "name":          dataset.name,
            "evidence_type": dataset.evidence_type,
        },
        ip_address  = request.client.host if request.client else None,
    )
    return DatasetResponse.model_validate(dataset)


@router.get(
    "/datasets/{dataset_id}",
    response_model = DatasetResponse,
    summary        = "Get dataset details",
)
async def get_dataset(
    dataset_id:   int,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """Retrieve metadata for a single dataset by ID."""
    dataset = await ml_service.get_dataset_or_404(db, dataset_id)
    return DatasetResponse.model_validate(dataset)


@router.delete(
    "/datasets/{dataset_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary     = "Delete a dataset and its files",
)
async def delete_dataset(
    dataset_id:   int,
    request:      Request,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """
    Permanently delete a dataset and remove its files from disk.
    Training jobs that used this dataset are preserved (FK set to NULL).
    """
    await create_log(
        db          = db,
        action_type = "dataset_deleted",
        user_id     = current_user.id,
        details     = {"dataset_id": dataset_id},
        ip_address  = request.client.host if request.client else None,
    )
    await ml_service.delete_dataset(db, dataset_id)


# ─────────────────────────────────────────────────────────────────────────────
# Model versions
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/models",
    response_model = ModelVersionListResponse,
    summary        = "List trained model versions",
)
async def list_models(
    current_user:  AIOrAdminUser,
    page:          int           = Query(1,  ge=1),
    limit:         int           = Query(20, ge=1, le=100),
    evidence_type: Optional[str] = Query(None),
    db:            AsyncSession  = Depends(get_db),
):
    """
    Returns model versions ordered newest-first.
    The currently active version for each evidence_type has `is_active=True`.
    """
    versions, total = await ml_service.list_model_versions(
        db            = db,
        page          = page,
        limit         = limit,
        evidence_type = evidence_type,
    )
    return ModelVersionListResponse(
        versions = [ModelVersionResponse.model_validate(v) for v in versions],
        total    = total,
        page     = page,
        limit    = limit,
    )


@router.get(
    "/models/{model_id}",
    response_model = ModelVersionResponse,
    summary        = "Get model version details",
)
async def get_model(
    model_id:     int,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """Retrieve full metadata for a model version including all metrics."""
    model = await ml_service.get_model_or_404(db, model_id)
    return ModelVersionResponse.model_validate(model)


@router.post(
    "/models/{model_id}/activate",
    response_model = ModelVersionResponse,
    summary        = "Set model version as the active inference model",
)
async def activate_model(
    model_id:     int,
    request:      Request,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """
    Activate a model version for live inference.

    - Only one version per evidence_type can be active at a time.
    - All other versions of the same evidence_type are automatically
      deactivated.
    - The in-memory inference engine is hot-swapped immediately if loaded.
    """
    model = await ml_service.activate_model(db, model_id)

    await create_log(
        db          = db,
        action_type = "model_activated",
        user_id     = current_user.id,
        details     = {
            "model_id":      model_id,
            "version":       model.version,
            "evidence_type": model.evidence_type,
        },
        ip_address  = request.client.host if request.client else None,
    )
    return ModelVersionResponse.model_validate(model)


# ─────────────────────────────────────────────────────────────────────────────
# Training jobs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/jobs",
    response_model = TrainingJobListResponse,
    summary        = "List training jobs",
)
async def list_jobs(
    current_user:  AIOrAdminUser,
    page:          int           = Query(1,  ge=1),
    limit:         int           = Query(20, ge=1, le=100),
    evidence_type: Optional[str] = Query(None),
    job_status:    Optional[str] = Query(None, alias="status",
                                         description="queued | running | completed | failed"),
    db:            AsyncSession  = Depends(get_db),
):
    """
    Returns training jobs ordered newest-first.

    Filterable by:
    - **evidence_type**: fingerprint | toolmark
    - **status**: queued | running | completed | failed
    """
    jobs, total = await ml_service.list_jobs(
        db            = db,
        page          = page,
        limit         = limit,
        evidence_type = evidence_type,
        job_status    = job_status,
    )
    job_responses = [await _job_response(j, db) for j in jobs]
    return TrainingJobListResponse(
        jobs  = job_responses,
        total = total,
        page  = page,
        limit = limit,
    )


@router.post(
    "/jobs",
    response_model = TrainingJobResponse,
    status_code    = status.HTTP_202_ACCEPTED,
    summary        = "Launch a new training run",
)
async def launch_training_job(
    payload:      TrainingJobCreate,
    request:      Request,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """
    Launch a new training job.

    - The dataset must be in `status=ready`.
    - Only one job per evidence_type can run at a time.
    - Returns 202 Accepted; the job starts asynchronously.
    - Poll GET /ml/jobs/:id to track progress.

    `config` is an optional dict of hyperparameters passed directly to
    the training engine (e.g. `{"lr": 0.001, "batch_size": 32}`).
    """
    job = await ml_service.create_training_job(
        db      = db,
        payload = payload,
        user_id = current_user.id,
    )

    await create_log(
        db          = db,
        action_type = "training_job_launched",
        user_id     = current_user.id,
        details     = {
            "job_id":        job.id,
            "name":          job.name,
            "evidence_type": job.evidence_type,
            "dataset_id":    job.dataset_id,
            "epochs":        job.epochs_total,
        },
        ip_address  = request.client.host if request.client else None,
    )
    return await _job_response(job, db)


@router.get(
    "/jobs/{job_id}",
    response_model = TrainingJobResponse,
    summary        = "Get training job details (poll for live progress)",
)
async def get_job(
    job_id:       int,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """
    Retrieve the current state of a training job.

    The dashboard polls this endpoint every few seconds while a job is
    running to display a live progress bar and epoch counter.
    """
    job = await ml_service.get_job_or_404(db, job_id)
    return await _job_response(job, db)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model = TrainingJobResponse,
    summary        = "Cancel a queued or running training job",
)
async def cancel_job(
    job_id:       int,
    request:      Request,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """
    Cancel a job in `queued` or `running` state.
    The job is marked as `failed` with error_message='Cancelled by admin.'
    Already `completed` or `failed` jobs cannot be cancelled.
    """
    job = await ml_service.cancel_job(db, job_id)

    await create_log(
        db          = db,
        action_type = "training_job_cancelled",
        user_id     = current_user.id,
        details     = {"job_id": job_id},
        ip_address  = request.client.host if request.client else None,
    )
    return await _job_response(job, db)


@router.patch(
    "/jobs/{job_id}/progress",
    response_model = TrainingJobResponse,
    summary        = "Internal: update job progress (called by training worker)",
    include_in_schema = False,   # hide from public Swagger docs
)
async def update_job_progress(
    job_id:       int,
    payload:      TrainingJobProgressUpdate,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """
    Called by the background training process to stream progress updates.
    Not intended for direct use by the frontend or external clients.

    Accepts partial updates — only provided fields are changed.
    When status transitions to 'completed', wire `complete_job_and_register_model`
    inside the training task instead of calling this endpoint directly.
    """
    job = await ml_service.update_job_progress(db, job_id, payload)
    return await _job_response(job, db)


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/evaluate",
    response_model = EvaluationListResponse,
    summary        = "List evaluation results",
)
async def list_evaluations(
    current_user:  AIOrAdminUser,
    page:          int           = Query(1,  ge=1),
    limit:         int           = Query(20, ge=1, le=100),
    model_id:      Optional[int] = Query(None),
    evidence_type: Optional[str] = Query(None),
    db:            AsyncSession  = Depends(get_db),
):
    """Returns evaluation runs ordered newest-first."""
    evals, total = await ml_service.list_evaluations(
        db            = db,
        page          = page,
        limit         = limit,
        model_id      = model_id,
        evidence_type = evidence_type,
    )
    return EvaluationListResponse(
        evaluations = [EvaluationResponse.model_validate(e) for e in evals],
        total       = total,
        page        = page,
        limit       = limit,
    )


@router.post(
    "/evaluate",
    response_model = EvaluationResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Run a model against an evaluation dataset",
)
async def run_evaluation(
    payload:      EvaluationCreate,
    request:      Request,
    current_user: AIOrAdminUser,
    db:           AsyncSession = Depends(get_db),
):
    """
    Evaluate a trained model against a labelled dataset.

    - The model and dataset must share the same `evidence_type`.
    - The dataset must be in `status=ready`.
    - Returns accuracy, precision, recall, and F1 score.
    - The full confusion matrix is included in `details`.

    **Note:** Until `ai_engine.evaluation` is integrated in `ml_service.py`,
    this returns stub zero-metrics. Connect the real pipeline by replacing
    the stub block in `ml_service.create_evaluation`.
    """
    evaluation = await ml_service.create_evaluation(
        db      = db,
        payload = payload,
        user_id = current_user.id,
    )

    await create_log(
        db          = db,
        action_type = "model_evaluated",
        user_id     = current_user.id,
        details     = {
            "evaluation_id": evaluation.id,
            "model_id":      evaluation.model_id,
            "dataset_id":    evaluation.dataset_id,
            "accuracy":      evaluation.accuracy,
        },
        ip_address  = request.client.host if request.client else None,
    )
    return EvaluationResponse.model_validate(evaluation)


@router.get(
    "/evaluate/{evaluation_id}",
    response_model = EvaluationResponse,
    summary        = "Get evaluation result details",
)
async def get_evaluation(
    evaluation_id: int,
    current_user:  AIOrAdminUser,
    db:            AsyncSession = Depends(get_db),
):
    """Retrieve the full results of a single evaluation run."""
    evaluation = await ml_service.get_evaluation_or_404(db, evaluation_id)
    return EvaluationResponse.model_validate(evaluation)