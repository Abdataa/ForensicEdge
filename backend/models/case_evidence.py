# backend/app/models/case_evidence.py
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base

class CaseEvidence(Base):
    __tablename__ = "case_evidence"
    
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), primary_key=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey("forensic_images.image_id", ondelete="CASCADE"), primary_key=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
    linked_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    
    # Relationships
    case = relationship("Case", back_populates="evidence_links")
    image = relationship("ForensicImage", back_populates="case_links")
    linker = relationship("User")