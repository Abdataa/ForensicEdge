# backend/app/models/audit_log.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid
import enum

class ActionType(str, enum.Enum):
    # Authentication
    login_success = "login_success"
    login_failed = "login_failed"
    logout = "logout"
    password_change = "password_change"
    
    # User Management
    user_created = "user_created"
    user_updated = "user_updated"
    user_deactivated = "user_deactivated"
    user_activated = "user_activated"
    role_changed = "role_changed"
    
    # Evidence
    image_uploaded = "image_uploaded"
    image_deleted = "image_deleted"
    image_preprocessed = "image_preprocessed"
    features_extracted = "features_extracted"
    
    # Analysis
    similarity_compared = "similarity_compared"
    report_generated = "report_generated"
    report_downloaded = "report_downloaded"
    feedback_submitted = "feedback_submitted"
    
    # AI Model
    model_training_started = "model_training_started"
    model_training_completed = "model_training_completed"
    model_deployed = "model_deployed"
    dataset_uploaded = "dataset_uploaded"
    
    # System
    system_backup = "system_backup"
    system_restore = "system_restore"
    settings_changed = "settings_changed"

action_type_enum = ENUM(ActionType, name="action_type_enum", create_type=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Action information
    action = Column(action_type_enum, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    # Who performed the action
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_email = Column(String(100), nullable=True)
    user_role = Column(String(50), nullable=True)
    
    # Target of the action
    target_id = Column(String(100), nullable=True)
    target_type = Column(String(50), nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(200), nullable=True)
    request_path = Column(String(200), nullable=True)
    request_method = Column(String(10), nullable=True)
    
    # Detailed data (JSONB)
    details = Column(JSONB, default=dict)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    
    # Result
    status = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'timestamp'),
        Index('idx_audit_action_time', 'action', 'timestamp'),
        Index('idx_audit_target', 'target_type', 'target_id'),
    )
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action.value} at {self.timestamp}>"