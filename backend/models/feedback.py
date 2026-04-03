# backend/app/models/feedback.py
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean, Text, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid
import enum

class FeedbackType(str, enum.Enum):
    CORRECT_MATCH = "correct_match"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    POOR_QUALITY = "poor_quality"
    OTHER = "other"

class FeedbackPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# PostgreSQL ENUMs
feedback_type_enum = ENUM(FeedbackType, name="feedback_type_enum", create_type=True)
feedback_priority_enum = ENUM(FeedbackPriority, name="feedback_priority_enum", create_type=True)

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    similarity_result_id = Column(UUID(as_uuid=True), ForeignKey("similarity_results.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Feedback content
    feedback_type = Column(feedback_type_enum, nullable=False)
    priority = Column(feedback_priority_enum, default=FeedbackPriority.MEDIUM)
    comment = Column(Text, nullable=False)
    
    # AI prediction vs Analyst decision
    ai_score = Column(Float)
    ai_decision = Column(String(20))
    analyst_decision = Column(String(20))
    
    # For retraining (JSONB)
    feedback_metadata = Column("metadata", JSONB, default=dict)
    used_for_retraining = Column(Boolean, default=False)
    retraining_batch_id = Column(String(50), nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_similarity', 'id'),
        Index('idx_feedback_type', 'feedback_type'),
        Index('idx_feedback_priority', 'priority'),
        Index('idx_feedback_retraining', 'used_for_retraining'),
    )
    
    # Relationships
    similarity_result = relationship("SimilarityResult", back_populates="feedback")
    user = relationship("User", back_populates="feedback", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

class AIModel(Base):
    __tablename__ = "ai_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Model identification
    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    
    # Model files
    model_path = Column(String(500), nullable=False)
    model_config = Column(JSONB, default=dict)
    model_weights_hash = Column(String(64), nullable=True)
    
    # Training information
    trained_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    trained_on = Column(DateTime(timezone=True), server_default=func.now())
    training_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    training_duration = Column(Float)  # in seconds
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
        Index('idx_ai_models_version', 'version'),
        Index('idx_ai_models_active', 'is_active'),
    )
    
    # Relationships
    trainer = relationship("User", foreign_keys=[trained_by])
    training_dataset = relationship("Dataset", back_populates="trained_models")
    feature_sets = relationship("FeatureSet", back_populates="model")
    similarity_results = relationship("SimilarityResult", back_populates="model")