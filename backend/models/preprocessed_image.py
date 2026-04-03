# backend/models/preprocessed_image.py
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid


class PreprocessedImage(Base):
    __tablename__ = "preprocessed_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Original image reference
    original_image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("forensic_images.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Processed file
    processed_filename = Column(String(255), nullable=False)
    processed_path = Column(String(500), nullable=False)
    processed_file_hash = Column(String(64), nullable=True)

    # Processing parameters (JSONB)
    enhancement_techniques = Column(JSONB, default=list)
    parameters = Column(JSONB, default=dict)

    # Quality metrics
    quality_score = Column(Float)  # 0-100
    processing_time = Column(Float)  # in seconds

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_preprocessed_original", "original_image_id"),)

    original = relationship("ForensicImage", back_populates="preprocessed")
    user = relationship("User", back_populates="preprocessed_images")
