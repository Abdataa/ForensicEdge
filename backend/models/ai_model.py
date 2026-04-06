from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid


class AIModel(Base):
    __tablename__ = "ai_models"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Model identification
    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)

    # Model storage
    model_path = Column(String(500), nullable=False)
    model_config = Column(JSONB, default=dict)
    model_weights_hash = Column(String(64), nullable=True)

    # Training info
    trained_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    trained_on = Column(DateTime(timezone=True), server_default=func.now())
    training_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    training_duration = Column(Float)  # seconds
    training_parameters = Column(JSONB, default=dict)

    # Performance metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    false_match_rate = Column(Float)
    false_non_match_rate = Column(Float)
    metrics = Column(JSONB, default=dict)

    # Status
    status = Column(String(20), default="training")  # training, trained, deployed, archived
    is_active = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index("idx_ai_models_version", "version"),
        Index("idx_ai_models_active", "is_active"),
    )

    # Relationships
    trainer = relationship("User", foreign_keys=[trained_by])
    training_dataset = relationship("Dataset", back_populates="trained_models")
    similarity_results = relationship("SimilarityResult", back_populates="model")