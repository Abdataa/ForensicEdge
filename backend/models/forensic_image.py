# backend/app/models/forensic_image.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid
import enum

class ImageType(str, enum.Enum):
    fingerprint = "fingerprint"
    toolmark = "toolmark"

class ImageQuality(str, enum.Enum):
    excellent = "excellent"
    good = "good"
    fair = "fair"
    poor = "poor"

class ProcessingStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    preprocessed = "preprocessed"
    features_extracted = "features_extracted"
    analyzed = "analyzed"
    failed = "failed"

# PostgreSQL ENUMs
image_type_enum = ENUM(ImageType, name="image_type_enum", create_type=True)
image_quality_enum = ENUM(ImageQuality, name="image_quality_enum", create_type=True)
processing_status_enum = ENUM(ProcessingStatus, name="processing_status_enum", create_type=True)

class ForensicImage(Base):
    __tablename__ = "forensic_images"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # File Information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String(50), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA-256 for integrity
    
    # Image Metadata
    image_type = Column(image_type_enum, nullable=False)
    quality = Column(image_quality_enum, default=ImageQuality.good)
    width = Column(Integer)
    height = Column(Integer)
    dpi = Column(Integer)
    
    # Processing Status
    status = Column(processing_status_enum, default=ProcessingStatus.uploaded)
    processing_time = Column(Float)  # in seconds
    
    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    case_id = Column(String(50), nullable=True, index=True)
    
    # Metadata (JSONB for flexibility)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, default=list)
    image_metadata = Column("metadata", JSONB, default=dict)
    exif_data = Column(JSONB, nullable=True)  # Camera/exif metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_forensic_images_user', 'user_id'),
        Index('idx_forensic_images_type_status', 'image_type', 'status'),
        Index('idx_forensic_images_case', 'case_id'),
        Index('idx_forensic_images_created', 'created_at'),
    )
    
    # Relationships
    user = relationship("User", back_populates="images")
    preprocessed = relationship("PreprocessedImage", uselist=False, back_populates="original", cascade="all, delete-orphan")
    feature_sets = relationship("FeatureSet", back_populates="image", cascade="all, delete-orphan")
    similarity_results_as_image1 = relationship(
        "SimilarityResult", 
        foreign_keys="SimilarityResult.image1_id",
        back_populates="image1",
        cascade="all, delete-orphan"
    )
    case_links = relationship(
    "CaseEvidence",
    back_populates="image",
    cascade="all, delete-orphan"
)
    similarity_results_as_image2 = relationship(
        "SimilarityResult", 
        foreign_keys="SimilarityResult.image2_id",
        back_populates="image2",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<ForensicImage {self.filename} ({self.image_type.value})>"