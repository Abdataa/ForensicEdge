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
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    
    # User Management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
    USER_ACTIVATED = "user_activated"
    ROLE_CHANGED = "role_changed"
    
    # Evidence
    IMAGE_UPLOADED = "image_uploaded"
    IMAGE_DELETED = "image_deleted"
    IMAGE_PREPROCESSED = "image_preprocessed"
    FEATURES_EXTRACTED = "features_extracted"
    
    # Analysis
    SIMILARITY_COMPARED = "similarity_compared"
    REPORT_GENERATED = "report_generated"
    REPORT_DOWNLOADED = "report_downloaded"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    
    # AI Model
    MODEL_TRAINING_STARTED = "model_training_started"
    MODEL_TRAINING_COMPLETED = "model_training_completed"
    MODEL_DEPLOYED = "model_deployed"
    DATASET_UPLOADED = "dataset_uploaded"
    
    # System
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    SETTINGS_CHANGED = "settings_changed"

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