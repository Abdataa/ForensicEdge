# backend/models/report.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    similarity_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("similarity_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    report_filename = Column(String(255), nullable=False)
    report_path = Column(String(500), nullable=False)
    report_format = Column(String(10), default="PDF")
    report_size = Column(Integer)
    report_hash = Column(String(64), nullable=True)

    report_summary = Column(JSONB, default=dict)
    report_data = Column(JSONB, default=dict)

    is_shared = Column(Boolean, default=False)
    share_token = Column(String(100), unique=True, nullable=True)
    share_expiry = Column(DateTime(timezone=True), nullable=True)
    download_count = Column(Integer, default=0)

    case_number = Column(String(50), nullable=True)
    includes_images = Column(Boolean, default=True)
    includes_charts = Column(Boolean, default=True)

    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    downloaded_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_reports_similarity", "similarity_result_id"),
        Index("idx_reports_user", "user_id"),
        Index("idx_reports_share_token", "share_token"),
    )

    similarity_result = relationship("SimilarityResult", back_populates="reports")
    user = relationship("User", back_populates="reports")
