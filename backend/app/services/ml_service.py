"""
backend/app/services/ml_service.py
────────────────────────────────────
Business logic for the ML-Ops subsystem.

Responsibilities
─────────────────
    Dataset management    — save zip, unpack, count images, compute size
    Training job lifecycle— create, start, progress updates, cancel, complete
    Model version mgmt    — register checkpoint, activate (exclusive per type)
    Evaluation            — run metrics against a dataset, persist results

Training integration
─────────────────────
The actual PyTorch training happens in ai_engine/ (already exists).
`launch_training_job` spawns a background asyncio task that calls the
existing training pipeline and streams progress back to the DB.

If you switch to Celery later, only `_run_training_task` needs to change —
the rest of the service layer stays identical.

Storage layout (all paths relative to settings.STORAGE_ROOT)
──────────────────────────────────────────────────────────────
    ml/datasets/<dataset_id>/          — unpacked images
    ml/weights/<evidence_type>/        — model .pth files
"""

from __future__ import annotations

import asyncio
import io
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib  import Path
from typing   import IO, List, Optional, Tuple

from fastapi          import HTTPException, UploadFile, status
from sqlalchemy       import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config  import settings
from app.models.ml    import MlDataset, MlEvaluation, MlModelVersion, MlTrainingJob
from app.schemas.ml_schema import (
    DatasetCreate,
    EvaluationCreate,
    TrainingJobCreate,
    TrainingJobProgressUpdate,
)


# ─────────────────────────────────────────────────────────────────────────────
# Storage helpers
# ─────────────────────────────────────────────────────────────────────────────

def _storage_root() -> Path:
    """Return the absolute storage root from settings."""
    root = Path(getattr(settings, "STORAGE_ROOT", "storage"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dataset_dir(dataset_id: int) -> Path:
    d = _storage_root() / "ml" / "datasets" / str(dataset_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _weights_dir(evidence_type: str) -> Path:
    d = _storage_root() / "ml" / "weights" / evidence_type
    d.mkdir(parents=True, exist_ok=True)
    return d


def _count_images_in_dir(directory: Path) -> int:
    """Count image files (jpg, jpeg, png, bmp, tiff) recursively."""
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
    return sum(
        1 for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in image_exts
    )


def _dir_size_mb(directory: Path) -> float:
    total_bytes = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
    return round(total_bytes / (1024 * 1024), 2)


# ─────────────────────────────────────────────────────────────────────────────
# Dataset service
# ─────────────────────────────────────────────────────────────────────────────

async def create_dataset(
    db:      AsyncSession,
    payload: DatasetCreate,
    file:    UploadFile,
    user_id: int,
) -> MlDataset:
    """
    1. Persist a dataset record with status='processing'.
    2. Save and unpack the uploaded zip in a background task.
    3. Update image_count, size_mb, status once unpacking finishes.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Dataset must be a .zip archive containing image files.",
        )

    dataset = MlDataset(
        name          = payload.name,
        description   = payload.description,
        evidence_type = payload.evidence_type,
        status        = "processing",
        created_by    = user_id,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    # Fire-and-forget background task — does not block the HTTP response
    asyncio.create_task(
        _unpack_dataset_zip(db_id=dataset.id, file_obj=await file.read())
    )

    return dataset


async def _unpack_dataset_zip(db_id: int, file_obj: bytes) -> None:
    """
    Background task: unpack zip, count images, update DB record.
    Runs entirely outside the request/response cycle.
    """
    from app.core.database import AsyncSessionLocal  # avoid circular import

    async with AsyncSessionLocal() as db:
        try:
            dest = _dataset_dir(db_id)
            zip_buf = io.BytesIO(file_obj)

            if not zipfile.is_zipfile(zip_buf):
                raise ValueError("Uploaded file is not a valid zip archive.")

            zip_buf.seek(0)
            with zipfile.ZipFile(zip_buf) as zf:
                # Security: reject absolute paths / path traversal
                for member in zf.namelist():
                    if os.path.isabs(member) or ".." in Path(member).parts:
                        raise ValueError(f"Unsafe path in zip: {member}")
                zf.extractall(dest)

            image_count = _count_images_in_dir(dest)
            size_mb     = _dir_size_mb(dest)

            await db.execute(
                update(MlDataset)
                .where(MlDataset.id == db_id)
                .values(
                    status      = "ready",
                    image_count = image_count,
                    size_mb     = size_mb,
                    file_path   = str(dest.relative_to(_storage_root())),
                )
            )
        except Exception as exc:
            await db.execute(
                update(MlDataset)
                .where(MlDataset.id == db_id)
                .values(status="error", error_message=str(exc))
            )
        finally:
            await db.commit()


async def list_datasets(
    db:            AsyncSession,
    page:          int = 1,
    limit:         int = 20,
    evidence_type: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> Tuple[List[MlDataset], int]:
    limit  = min(limit, 100)
    offset = (page - 1) * limit
    q      = select(MlDataset)

    if evidence_type:
        q = q.where(MlDataset.evidence_type == evidence_type)
    if status_filter:
        q = q.where(MlDataset.status == status_filter)

    total_q = await db.execute(q.with_only_columns(func.count(MlDataset.id)))
    total   = total_q.scalar() or 0

    rows    = await db.execute(q.order_by(desc(MlDataset.created_at)).offset(offset).limit(limit))
    return rows.scalars().all(), total


async def get_dataset_or_404(db: AsyncSession, dataset_id: int) -> MlDataset:
    row = await db.execute(select(MlDataset).where(MlDataset.id == dataset_id))
    ds  = row.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Dataset {dataset_id} not found.")
    return ds


async def delete_dataset(db: AsyncSession, dataset_id: int) -> None:
    ds = await get_dataset_or_404(db, dataset_id)

    # Remove files from disk
    if ds.file_path:
        full_path = _storage_root() / ds.file_path
        if full_path.exists():
            shutil.rmtree(full_path, ignore_errors=True)

    await db.delete(ds)
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Training job service
# ─────────────────────────────────────────────────────────────────────────────

async def create_training_job(
    db:      AsyncSession,
    payload: TrainingJobCreate,
    user_id: int,
) -> MlTrainingJob:
    """
    Validate the dataset, create a job record in 'queued' state,
    then spawn a background training task.
    """
    dataset = await get_dataset_or_404(db, payload.dataset_id)

    if dataset.status != "ready":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Dataset {dataset.id} is not ready (status={dataset.status!r}).",
        )

    if dataset.evidence_type != payload.evidence_type:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Dataset evidence_type ({dataset.evidence_type!r}) does not match "
            f"requested evidence_type ({payload.evidence_type!r}).",
        )

    # Check for an already-running job of the same type
    running_q = await db.execute(
        select(MlTrainingJob).where(
            MlTrainingJob.evidence_type == payload.evidence_type,
            MlTrainingJob.status       == "running",
        )
    )
    if running_q.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A training job for {payload.evidence_type!r} is already running. "
            "Wait for it to finish or cancel it first.",
        )

    job = MlTrainingJob(
        name          = payload.name,
        evidence_type = payload.evidence_type,
        dataset_id    = dataset.id,
        epochs_total  = payload.epochs,
        epochs_done   = 0,
        progress_pct  = 0,
        status        = "queued",
        config        = payload.config,
        created_by    = user_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Spawn background training
    asyncio.create_task(_run_training_task(job_id=job.id))

    return job


async def _run_training_task(job_id: int) -> None:
    """
    Background task: drive the existing ai_engine training pipeline.

    Progress is written to the DB at each epoch so the frontend can poll
    GET /ml/jobs/:id and show a live progress bar.

    If ai_engine training is not yet wired up, this logs a warning and
    marks the job as failed so the API stays consistent.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        row = await db.execute(select(MlTrainingJob).where(MlTrainingJob.id == job_id))
        job = row.scalar_one_or_none()
        if job is None:
            return

        # Mark as running
        job.status     = "running"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # ── Integration point ──────────────────────────────────────────
            # Replace this block with your actual training call.
            # The function should be an async generator that yields
            # (epoch, accuracy, val_loss) tuples after each epoch.
            #
            # Example using the existing ai_engine:
            #
            #   from ai_engine.training.train import train_epoch_generator
            #   dataset_path = _dataset_dir(job.dataset_id)
            #   async for epoch, acc, loss in train_epoch_generator(
            #       evidence_type = job.evidence_type,
            #       dataset_path  = dataset_path,
            #       epochs        = job.epochs_total,
            #       config        = job.config or {},
            #   ):
            #       pct = int((epoch / job.epochs_total) * 100)
            #       await db.execute(
            #           update(MlTrainingJob).where(MlTrainingJob.id == job_id)
            #           .values(epochs_done=epoch, progress_pct=pct,
            #                   accuracy=acc, val_loss=loss)
            #       )
            #       await db.commit()
            # ──────────────────────────────────────────────────────────────

            # Stub: emit a single progress update so the dashboard is not stuck
            await db.execute(
                update(MlTrainingJob).where(MlTrainingJob.id == job_id)
                .values(
                    status      = "failed",
                    finished_at = datetime.now(timezone.utc),
                    error_message = (
                        "Training engine not yet integrated. "
                        "Connect ai_engine.training inside _run_training_task()."
                    ),
                )
            )
            await db.commit()

        except Exception as exc:
            await db.execute(
                update(MlTrainingJob).where(MlTrainingJob.id == job_id)
                .values(
                    status        = "failed",
                    finished_at   = datetime.now(timezone.utc),
                    error_message = str(exc)[:2000],
                )
            )
            await db.commit()


async def list_jobs(
    db:            AsyncSession,
    page:          int = 1,
    limit:         int = 20,
    evidence_type: Optional[str] = None,
    job_status:    Optional[str] = None,
) -> Tuple[List[MlTrainingJob], int]:
    limit  = min(limit, 100)
    offset = (page - 1) * limit
    q      = select(MlTrainingJob)

    if evidence_type:
        q = q.where(MlTrainingJob.evidence_type == evidence_type)
    if job_status:
        q = q.where(MlTrainingJob.status == job_status)

    total_q = await db.execute(q.with_only_columns(func.count(MlTrainingJob.id)))
    total   = total_q.scalar() or 0

    rows = await db.execute(
        q.order_by(desc(MlTrainingJob.created_at)).offset(offset).limit(limit)
    )
    return rows.scalars().all(), total


async def get_job_or_404(db: AsyncSession, job_id: int) -> MlTrainingJob:
    row = await db.execute(select(MlTrainingJob).where(MlTrainingJob.id == job_id))
    job = row.scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Training job {job_id} not found.")
    return job


async def cancel_job(db: AsyncSession, job_id: int) -> MlTrainingJob:
    job = await get_job_or_404(db, job_id)

    if job.status not in ("queued", "running"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot cancel a job with status={job.status!r}.",
        )

    job.status      = "failed"
    job.finished_at = datetime.now(timezone.utc)
    job.error_message = "Cancelled by admin."
    await db.commit()
    await db.refresh(job)
    return job


async def update_job_progress(
    db:      AsyncSession,
    job_id:  int,
    payload: TrainingJobProgressUpdate,
) -> MlTrainingJob:
    """Called by the training worker via PATCH /ml/jobs/:id/progress."""
    job = await get_job_or_404(db, job_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    # Auto-set timestamps
    if payload.status == "running" and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    if payload.status in ("completed", "failed") and job.finished_at is None:
        job.finished_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(job)
    return job


async def complete_job_and_register_model(
    db:          AsyncSession,
    job_id:      int,
    accuracy:    float,
    val_loss:    float,
    weight_path: str,
    metrics:     dict,
    user_id:     int,
) -> MlModelVersion:
    """
    Called when training completes successfully.
    1. Marks the job as completed.
    2. Creates a new MlModelVersion record.
    """
    job = await get_job_or_404(db, job_id)

    job.status      = "completed"
    job.accuracy    = accuracy
    job.val_loss    = val_loss
    job.finished_at = datetime.now(timezone.utc)
    job.progress_pct = 100
    job.epochs_done  = job.epochs_total

    # Derive next semantic version for this evidence type
    version_str = await _next_version(db, job.evidence_type)

    model = MlModelVersion(
        version         = version_str,
        evidence_type   = job.evidence_type,
        accuracy        = accuracy,
        val_loss        = val_loss,
        weight_path     = weight_path,
        metrics         = metrics,
        is_active       = False,     # must be explicitly activated
        training_job_id = job.id,
        created_by      = user_id,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


async def _next_version(db: AsyncSession, evidence_type: str) -> str:
    """Generate the next semantic version string (v1.0, v1.1, …)."""
    row = await db.execute(
        select(func.count(MlModelVersion.id))
        .where(MlModelVersion.evidence_type == evidence_type)
    )
    count = row.scalar() or 0
    major = (count // 10) + 1
    minor = count % 10
    return f"v{major}.{minor}"


# ─────────────────────────────────────────────────────────────────────────────
# Model version service
# ─────────────────────────────────────────────────────────────────────────────

async def list_model_versions(
    db:            AsyncSession,
    page:          int = 1,
    limit:         int = 20,
    evidence_type: Optional[str] = None,
) -> Tuple[List[MlModelVersion], int]:
    limit  = min(limit, 100)
    offset = (page - 1) * limit
    q      = select(MlModelVersion)

    if evidence_type:
        q = q.where(MlModelVersion.evidence_type == evidence_type)

    total_q = await db.execute(q.with_only_columns(func.count(MlModelVersion.id)))
    total   = total_q.scalar() or 0

    rows = await db.execute(
        q.order_by(desc(MlModelVersion.created_at)).offset(offset).limit(limit)
    )
    return rows.scalars().all(), total


async def get_model_or_404(db: AsyncSession, model_id: int) -> MlModelVersion:
    row = await db.execute(select(MlModelVersion).where(MlModelVersion.id == model_id))
    mv  = row.scalar_one_or_none()
    if mv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Model version {model_id} not found.")
    return mv


async def activate_model(
    db:       AsyncSession,
    model_id: int,
) -> MlModelVersion:
    """
    Activate a model version.
    Exactly one model per evidence_type is active at any time.
    Wrapped in a transaction: deactivate all others first, then activate.
    """
    model = await get_model_or_404(db, model_id)

    if model.is_active:
        return model   # already active — idempotent

    # Deactivate all versions of the same evidence type
    await db.execute(
        update(MlModelVersion)
        .where(MlModelVersion.evidence_type == model.evidence_type)
        .values(is_active=False)
    )

    # Activate the chosen version
    model.is_active = True
    await db.commit()
    await db.refresh(model)

    # Hot-swap the inference engine if it's already loaded in memory
    try:
        from ai_engine.inference.compare import get_engine
        get_engine(evidence_type=model.evidence_type, reload=True)
    except Exception:
        pass  # inference engine reload is best-effort

    return model


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation service
# ─────────────────────────────────────────────────────────────────────────────

async def create_evaluation(
    db:      AsyncSession,
    payload: EvaluationCreate,
    user_id: int,
) -> MlEvaluation:
    """
    Run the active model's inference engine against the evaluation dataset
    and persist the metrics.

    If the real evaluation pipeline is not yet integrated, returns a
    placeholder record with zero metrics rather than a 500 error.
    """
    model   = await get_model_or_404(db, payload.model_id)
    dataset = await get_dataset_or_404(db, payload.dataset_id)

    if dataset.status != "ready":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Dataset {dataset.id} is not ready (status={dataset.status!r}).",
        )

    if model.evidence_type != dataset.evidence_type:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Model and dataset must have the same evidence_type.",
        )

    # ── Integration point ─────────────────────────────────────────────────
    # Replace the stub below with the real evaluation call:
    #
    #   from ai_engine.evaluation.evaluate import run_evaluation
    #   dataset_path = _dataset_dir(dataset.id)
    #   result = await asyncio.to_thread(
    #       run_evaluation,
    #       evidence_type = model.evidence_type,
    #       weight_path   = model.weight_path,
    #       dataset_path  = str(dataset_path),
    #   )
    #   accuracy  = result["accuracy"]
    #   precision = result["precision"]
    #   recall    = result["recall"]
    #   f1_score  = result["f1"]
    #   details   = result           # full dict including confusion_matrix
    # ──────────────────────────────────────────────────────────────────────

    # Stub values — replace when ai_engine evaluation is wired up
    accuracy, precision, recall, f1_score = 0.0, 0.0, 0.0, 0.0
    details = {"note": "Evaluation engine not yet integrated."}

    evaluation = MlEvaluation(
        model_id      = model.id,
        dataset_id    = dataset.id,
        evidence_type = model.evidence_type,
        accuracy      = accuracy,
        precision     = precision,
        recall        = recall,
        f1_score      = f1_score,
        details       = details,
        created_by    = user_id,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


async def get_evaluation_or_404(db: AsyncSession, evaluation_id: int) -> MlEvaluation:
    row  = await db.execute(select(MlEvaluation).where(MlEvaluation.id == evaluation_id))
    ev   = row.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Evaluation {evaluation_id} not found.")
    return ev


async def list_evaluations(
    db:            AsyncSession,
    page:          int = 1,
    limit:         int = 20,
    model_id:      Optional[int] = None,
    evidence_type: Optional[str] = None,
) -> Tuple[List[MlEvaluation], int]:
    limit  = min(limit, 100)
    offset = (page - 1) * limit
    q      = select(MlEvaluation)

    if model_id:
        q = q.where(MlEvaluation.model_id == model_id)
    if evidence_type:
        q = q.where(MlEvaluation.evidence_type == evidence_type)

    total_q = await db.execute(q.with_only_columns(func.count(MlEvaluation.id)))
    total   = total_q.scalar() or 0

    rows = await db.execute(
        q.order_by(desc(MlEvaluation.created_at)).offset(offset).limit(limit)
    )
    return rows.scalars().all(), total