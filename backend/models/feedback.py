# backend/app/models/feedback.py
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean, Text, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid
import enum

class FeedbackType(str, enum.Enum):
    correct_match = "correct_match"
    false_positive = "false_positive"
    false_negative = "false_negative"
    poor_quality = "poor_quality"
    other = "other"

class FeedbackPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"

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
    priority = Column(feedback_priority_enum, default=FeedbackPriority.medium)
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
        Index('idx_feedback_similarity', 'similarity_result_id'),
        Index('idx_feedback_type', 'feedback_type'),
        Index('idx_feedback_priority', 'priority'),
        Index('idx_feedback_retraining', 'used_for_retraining'),
    )
    
    # Relationships
    similarity_result = relationship("SimilarityResult", back_populates="feedback")
    user = relationship("User", back_populates="feedback", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

