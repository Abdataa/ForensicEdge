# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid
import enum

class UserRole(str, enum.Enum):
    ANALYST = "analyst"
    ADMIN = "admin"
    AI_ENGINEER = "ai_engineer"

# PostgreSQL ENUM type
user_role_enum = ENUM(
    UserRole,
    name="user_role_enum",
    create_type=True
)

class User(Base):
    __tablename__ = "users"
    
   
    cases_assigned = relationship("Case", foreign_keys="[Case.assigned_to]", back_populates="assignee")
    cases_created = relationship("Case", foreign_keys="[Case.created_by]", back_populates="creator")
    # Primary Key using UUID for better distribution
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
      
    # Basic Information
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(user_role_enum, nullable=False, default=UserRole.ANALYST)
    
    # Professional Information
    badge_number = Column(String(50), unique=True, nullable=True)
    department = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_super_admin = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Preferences (JSONB for flexible storage)
    preferences = Column(JSONB, default={})
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_users_email_role', 'email', 'role'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    # Relationships
    images = relationship("ForensicImage", back_populates="user", cascade="all, delete-orphan")
    preprocessed_images = relationship("PreprocessedImage", back_populates="user")
    feature_sets = relationship("FeatureSet", back_populates="user")
    similarity_results = relationship("SimilarityResult", back_populates="user")
    reports = relationship("Report", back_populates="user")
   # Inside class User(Base):
    feedback = relationship("Feedback", back_populates="user", foreign_keys="[Feedback.user_id]" )
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")
    created_users = relationship("User", backref="creator", remote_side=[id])
    
    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    session_token = Column(String(500), unique=True, nullable=False)
    refresh_token = Column(String(500), unique=True, nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(String(200))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Index
    __table_args__ = (
        Index('idx_sessions_token', 'session_token'),
        Index('idx_sessions_user_expires', 'user_id', 'expires_at'),
    )
    
    # Relationship
    user = relationship("User")

class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    token = Column(String(100), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Index
    __table_args__ = (
        Index('idx_reset_token', 'token'),
    )
    
    # Relationship
    user = relationship("User")