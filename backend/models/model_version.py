# backend/app/models/model_version.py
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid

class ModelVersion(Base):
    __tablename__ = "model_versions"
    
    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(20), unique=True, nullable=False)
    accuracy = Column(Float)
    loss = Column(Float)
    created_on = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="training")  # training, trained, deployed, archived, failed
    
    # Additional fields
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    model_path = Column(String(500), nullable=False)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    false_match_rate = Column(Float)
    false_non_match_rate = Column(Float)
    training_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    trained_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    training_duration = Column(Float)
    training_parameters = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=False)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    training_dataset = relationship("Dataset", back_populates="model_versions")
    trainer = relationship("User")
    feature_sets = relationship("FeatureSet", foreign_keys="[FeatureSet.model_version_id]")