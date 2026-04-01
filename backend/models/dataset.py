# backend/models/dataset.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100))
    dataset_type = Column(String(50))

    dataset_path = Column(String(500), nullable=False)
    file_count = Column(Integer, default=0)
    size_mb = Column(Float)

    train_count = Column(Integer)
    val_count = Column(Integer)
    test_count = Column(Integer)

    dataset_metadata = Column("metadata", JSONB, default=dict)
    class_distribution = Column(JSONB, default=dict)

    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_datasets_type", "dataset_type"),
        Index("idx_datasets_public", "is_public"),
    )

    uploader = relationship("User", foreign_keys=[uploaded_by])
    trained_models = relationship("AIModel", back_populates="training_dataset")
    model_versions = relationship("ModelVersion", back_populates="training_dataset")
