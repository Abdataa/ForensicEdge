"""
backend/app/models/ml.py
─────────────────────────
SQLAlchemy ORM models for the AI-Engineer / ML-Ops subsystem.

Tables
──────
    ml_datasets         — uploaded training/evaluation datasets
    ml_model_versions   — trained model checkpoints + metrics
    ml_training_jobs    — training job lifecycle + progress
    ml_evaluations      — evaluation runs against a dataset

Design notes
────────────
- All PKs are plain integer sequences for consistency with the rest of the app.
- FKs to users.id use SET NULL on delete so job history is preserved even if
  the engineer account is deleted (same pattern as AuditLog).
- `config` and `metrics` columns are JSON so we never have to migrate the
  table when hyperparameters or metric names change.
- The `status` columns are plain VARCHAR rather than Postgres ENUM so Alembic
  migrations stay simple and the app works on SQLite for local dev.
- `file_path` columns store paths relative to the storage root defined in
  settings, not absolute paths, for portability.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float,
    ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# MlDataset
# ─────────────────────────────────────────────────────────────────────────────

class MlDataset(Base):
    """
    A labelled image dataset used for training or evaluation.

    Uploaded as a zip archive; the backend unpacks it into a storage
    directory and records metadata here.

    status values
    ─────────────
        processing  — zip is being unpacked / images are being validated
        ready       — dataset is available for training/evaluation
        error       — unpacking or validation failed (see `error_message`)
    """
    __tablename__ = "ml_datasets"

    id            = Column(Integer,     primary_key=True, index=True)
    name          = Column(String(255), nullable=False)
    description   = Column(Text,        nullable=True)
    evidence_type = Column(String(50),  nullable=False)   # fingerprint | toolmark
    image_count   = Column(Integer,     nullable=False, default=0)
    size_mb       = Column(Float,       nullable=False, default=0.0)
    file_path     = Column(String(512), nullable=True)    # relative path to unpacked dir
    status        = Column(String(20),  nullable=False, default="processing")
    error_message = Column(Text,        nullable=True)
    created_by    = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                           default=_utcnow, onupdate=_utcnow)

    # Relationships
    creator       = relationship("User",            foreign_keys=[created_by], lazy="select")
    training_jobs = relationship("MlTrainingJob",   back_populates="dataset",  lazy="select")
    evaluations   = relationship("MlEvaluation",    back_populates="dataset",  lazy="select")

    def __repr__(self) -> str:
        return f"<MlDataset id={self.id} name={self.name!r} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# MlModelVersion
# ─────────────────────────────────────────────────────────────────────────────

class MlModelVersion(Base):
    """
    A trained model checkpoint with evaluation metrics.

    Produced at the end of a successful MlTrainingJob.
    Only one version per evidence_type can be `is_active=True` at a time;
    the activation endpoint enforces this with a transaction.

    weight_path  — path to the .pth file, relative to storage root
    metrics      — full dict of all tracked metrics (accuracy, val_loss,
                   precision, recall, f1, confusion_matrix, …)
    """
    __tablename__ = "ml_model_versions"

    id               = Column(Integer,     primary_key=True, index=True)
    version          = Column(String(50),  nullable=False)          # "v2.4.1"
    evidence_type    = Column(String(50),  nullable=False, index=True)
    accuracy         = Column(Float,       nullable=False, default=0.0)  # 0-100
    val_loss         = Column(Float,       nullable=False, default=0.0)
    weight_path      = Column(String(512), nullable=True)
    metrics          = Column(JSON,        nullable=True)             # full metric dict
    notes            = Column(Text,        nullable=True)
    is_active        = Column(Boolean,     nullable=False, default=False, index=True)
    training_job_id  = Column(
        Integer,
        ForeignKey("ml_training_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by       = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at       = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    training_job  = relationship("MlTrainingJob",  foreign_keys=[training_job_id],
                                 back_populates="model_version", lazy="select")
    creator       = relationship("User",           foreign_keys=[created_by], lazy="select")
    evaluations   = relationship("MlEvaluation",   back_populates="model",    lazy="select")

    def __repr__(self) -> str:
        return (
            f"<MlModelVersion id={self.id} version={self.version!r} "
            f"evidence_type={self.evidence_type!r} active={self.is_active}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MlTrainingJob
# ─────────────────────────────────────────────────────────────────────────────

class MlTrainingJob(Base):
    """
    A training run lifecycle record.

    status values
    ─────────────
        queued      — created, waiting for a worker to pick it up
        running     — actively training; progress_pct / epochs_done update live
        completed   — finished successfully; model_version FK is set
        failed      — crashed; error_message has the traceback summary

    progress_pct is updated by the training worker (background task /
    Celery worker / subprocess) via PATCH /ml/jobs/:id/progress.
    The dashboard polls GET /ml/jobs/:id to show live updates.

    config  — hyperparameters passed to the trainer
              e.g. {"lr": 0.001, "batch_size": 32, "optimizer": "adam"}
    """
    __tablename__ = "ml_training_jobs"

    id            = Column(Integer,     primary_key=True, index=True)
    name          = Column(String(255), nullable=False)
    evidence_type = Column(String(50),  nullable=False, index=True)
    dataset_id    = Column(
        Integer,
        ForeignKey("ml_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status        = Column(String(20),  nullable=False, default="queued", index=True)
    progress_pct  = Column(Integer,     nullable=False, default=0)
    epochs_total  = Column(Integer,     nullable=False, default=50)
    epochs_done   = Column(Integer,     nullable=False, default=0)
    accuracy      = Column(Float,       nullable=True)   # null while running
    val_loss      = Column(Float,       nullable=True)
    error_message = Column(Text,        nullable=True)
    config        = Column(JSON,        nullable=True)   # hyperparameter dict
    created_by    = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at    = Column(DateTime(timezone=True), nullable=True)
    finished_at   = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    dataset       = relationship("MlDataset",      foreign_keys=[dataset_id],
                                 back_populates="training_jobs", lazy="select")
    creator       = relationship("User",           foreign_keys=[created_by], lazy="select")
    model_version = relationship("MlModelVersion", foreign_keys="MlModelVersion.training_job_id",
                                 back_populates="training_job",  lazy="select",
                                 uselist=False)

    def __repr__(self) -> str:
        return (
            f"<MlTrainingJob id={self.id} name={self.name!r} "
            f"status={self.status!r} progress={self.progress_pct}%>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MlEvaluation
# ─────────────────────────────────────────────────────────────────────────────

class MlEvaluation(Base):
    """
    The result of running a trained model against an evaluation dataset.

    Stores the standard binary-classification metrics.
    The full per-class breakdown / confusion matrix is in `details` JSON.
    """
    __tablename__ = "ml_evaluations"

    id            = Column(Integer,    primary_key=True, index=True)
    model_id      = Column(
        Integer,
        ForeignKey("ml_model_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id    = Column(
        Integer,
        ForeignKey("ml_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evidence_type = Column(String(50), nullable=False)
    accuracy      = Column(Float,      nullable=False, default=0.0)   # 0-100
    precision     = Column(Float,      nullable=False, default=0.0)
    recall        = Column(Float,      nullable=False, default=0.0)
    f1_score      = Column(Float,      nullable=False, default=0.0)
    details       = Column(JSON,       nullable=True)   # confusion matrix etc.
    created_by    = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    model   = relationship("MlModelVersion", foreign_keys=[model_id],
                           back_populates="evaluations", lazy="select")
    dataset = relationship("MlDataset",      foreign_keys=[dataset_id],
                           back_populates="evaluations", lazy="select")
    creator = relationship("User",           foreign_keys=[created_by], lazy="select")

    def __repr__(self) -> str:
        return (
            f"<MlEvaluation id={self.id} model_id={self.model_id} "
            f"accuracy={self.accuracy:.1f}%>"
        )