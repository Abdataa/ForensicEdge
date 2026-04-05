# backend/app/models/feature_set.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, BYTEA
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid
from models.model_version import ModelVersion
from models.forensic_image import ForensicImage

# If using pgvector extension
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
    # Fallback
    Vector = lambda dim: JSONB

class FeatureSet(Base):
    __tablename__ = "feature_sets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    model_version_id = Column( UUID(as_uuid=True),  ForeignKey("model_versions.model_id"),)
    # Image reference
    image_id = Column(UUID(as_uuid=True), ForeignKey("forensic_images.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Feature data - 64-dim embedding
    feature_vector = Column(JSONB, nullable=False)  # JSON array as backup
    
    # Vector for similarity search (if pgvector available)
    if VECTOR_AVAILABLE:
        embedding = Column(Vector(64), nullable=True)  # 64-dim vector
    
    # Feature details (JSONB for flexibility)
    minutiae_points = Column(JSONB, default=list)  # List of minutiae points
    minutiae_count = Column(Integer, default=0)
    ridge_flow_pattern = Column(JSONB, default=dict)
    core_points = Column(JSONB, default=list)
    singularity_points = Column(JSONB, default=list)
    
    # For toolmarks
    striations = Column(JSONB, default=list)
    edge_profile = Column(JSONB, default=dict)
    
    # Model information
    model_version = Column(String(50), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id"), nullable=True)
    confidence_scores = Column(JSONB, default=dict)
    
    # Quality metrics
    feature_quality_score = Column(Float)  # 0-100
    extraction_time = Column(Float)  # in seconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_feature_set_image', 'image_id'),
        Index('idx_feature_set_model', 'model_id'),
        Index('idx_feature_set_quality', 'feature_quality_score'),
    )
    
    # If pgvector, create vector index
    if VECTOR_AVAILABLE:
        __table_args__ = __table_args__ + (
            Index('idx_feature_embedding', embedding, postgresql_using='ivfflat'),
        )
    
    # Relationships
    image = relationship("ForensicImage", back_populates="feature_sets")
    user = relationship("User", back_populates="feature_sets")
    model = relationship("AIModel", back_populates="feature_sets")
    similarity_results = relationship("SimilarityResult", back_populates="feature_set")
    model_version = relationship("ModelVersion", back_populates="feature_sets")
    
    def __repr__(self):
        return f"<FeatureSet image:{self.image_id} features:{self.minutiae_count}>"