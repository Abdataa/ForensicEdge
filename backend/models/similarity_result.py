# backend/app/models/similarity_result.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid
import enum

class MatchConfidence(str, enum.Enum):
    high = "high"
    medium = "medium"
    low= "low"
    inconclusive = "inconclusive"

class MatchStatus(str, enum.Enum):
    match= "match"
    non_match = "non_match"
    inconclusive = "inconclusive"
    pending_review = "pending_review"

# PostgreSQL ENUMs
match_confidence_enum = ENUM(MatchConfidence, name="match_confidence_enum", create_type=True)
match_status_enum = ENUM(MatchStatus, name="match_status_enum", create_type=True)

class SimilarityResult(Base):
    __tablename__ = "similarity_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Compared images
    image1_id = Column(UUID(as_uuid=True), ForeignKey("forensic_images.id", ondelete="CASCADE"), nullable=False)
    image2_id = Column(UUID(as_uuid=True), ForeignKey("forensic_images.id", ondelete="CASCADE"), nullable=False)
    feature_set_id = Column(UUID(as_uuid=True), ForeignKey("feature_sets.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Similarity scores
    similarity_score = Column(Float, nullable=False)  # 0-100
    confidence = Column(match_confidence_enum, nullable=False)
    match_status = Column(match_status_enum, default=MatchStatus.pending_review)
    
    # Detailed analysis (JSONB)
    matched_features = Column(JSONB, default=list)
    matched_feature_count = Column(Integer, default=0)
    unmatched_features = Column(JSONB, default=list)
    feature_comparison_details = Column(JSONB, default=dict)
    
    # Quality metrics
    image1_quality_impact = Column(Float, default=1.0)
    image2_quality_impact = Column(Float, default=1.0)
    overall_quality_factor = Column(Float, default=1.0)
    
    # Model information
    model_version = Column(String(50), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id"), nullable=True)
    processing_time = Column(Float)  # in seconds
    
    # Analyst feedback
    analyst_verified = Column(Boolean, default=False)
    analyst_comment = Column(Text, nullable=True)
    analyst_decision = Column(match_status_enum, nullable=True)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    case_id = Column(String(50), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_similarity_images', 'image1_id', 'image2_id'),
        Index('idx_similarity_score', 'similarity_score'),
        Index('idx_similarity_confidence', 'confidence'),
        Index('idx_similarity_created', 'created_at'),
        Index('idx_similarity_user', 'user_id'),
        Index('idx_similarity_case', 'case_id'),
    )
    
    # Relationships
    image1 = relationship("ForensicImage", foreign_keys=[image1_id], back_populates="similarity_results_as_image1")
    image2 = relationship("ForensicImage", foreign_keys=[image2_id], back_populates="similarity_results_as_image2")
    feature_set = relationship("FeatureSet", back_populates="similarity_results")
    user = relationship("User", back_populates="similarity_results")
    model = relationship("AIModel", back_populates="similarity_results")
    reports = relationship("Report", back_populates="similarity_result")
    feedback = relationship("Feedback", back_populates="similarity_result")
    
    def __repr__(self):
        return f"<SimilarityResult {self.similarity_score}%>"