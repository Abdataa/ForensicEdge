# backend/app/models/system_config.py
from sqlalchemy import Column, String, Boolean, DateTime, Text, Index, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from core.database import Base
import uuid

class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Configuration
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSONB, nullable=False)
    
    # Metadata
    description = Column(String(500), nullable=True)
    category = Column(String(50), default="general")
    is_public = Column(Boolean, default=False)
    is_editable = Column(Boolean, default=True)
    
    # Tracking
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_config_category', 'category'),
    )

class SystemHealth(Base):
    __tablename__ = "system_health"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Health metrics
    component = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # healthy, degraded, down
    metric_name = Column(String(50))
    metric_value = Column(Float)
    metric_unit = Column(String(20))
    
    # Details (JSONB)
    message = Column(String(500), nullable=True)
    details = Column(JSONB, default=dict)
    
    # Timestamp
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_health_component', 'component'),
        Index('idx_health_time', 'checked_at'),
    )