# backend/app/models/case.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid

class Case(Base):
    __tablename__ = "cases"
    
    case_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(50), unique=True, nullable=False)
    case_metadata = Column("metadata", JSONB, default=dict)
    
    # Additional fields
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="open")  # open, closed, archived
    priority = Column(String(20), default="normal")  # high, medium, low, normal
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="cases_assigned")
    creator = relationship("User", foreign_keys=[created_by], back_populates="cases_created")
    evidence_links = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")