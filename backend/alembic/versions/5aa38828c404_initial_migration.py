# backend/alembic/versions/001_initial_migration.py
"""initial migration

Revision ID: 001
Revises: 
Create Date: 2026-03-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create ENUM types first
    op.execute("CREATE TYPE user_role_enum AS ENUM ('analyst', 'admin', 'ai_engineer')")
    op.execute("CREATE TYPE image_type_enum AS ENUM ('fingerprint', 'toolmark')")
    op.execute("CREATE TYPE image_quality_enum AS ENUM ('excellent', 'good', 'fair', 'poor')")
    op.execute("CREATE TYPE processing_status_enum AS ENUM ('uploaded', 'processing', 'preprocessed', 'features_extracted', 'analyzed', 'failed')")
    op.execute("CREATE TYPE match_confidence_enum AS ENUM ('high', 'medium', 'low', 'inconclusive')")
    op.execute("CREATE TYPE match_status_enum AS ENUM ('match', 'non_match', 'inconclusive', 'pending_review')")
    op.execute("CREATE TYPE feedback_type_enum AS ENUM ('correct_match', 'false_positive', 'false_negative', 'poor_quality', 'other')")
    op.execute("CREATE TYPE feedback_priority_enum AS ENUM ('high', 'medium', 'low')")
    op.execute("CREATE TYPE action_type_enum AS ENUM ('login_success', 'login_failed', 'logout', 'password_change', 'user_created', 'user_updated', 'user_deactivated', 'user_activated', 'role_changed', 'image_uploaded', 'image_deleted', 'image_preprocessed', 'features_extracted', 'similarity_compared', 'report_generated', 'report_downloaded', 'feedback_submitted', 'model_training_started', 'model_training_completed', 'model_deployed', 'dataset_uploaded', 'system_backup', 'system_restore', 'settings_changed')")

    # Create tables
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(200), nullable=False),
        sa.Column('role', postgresql.ENUM(name='user_role_enum', create_type=False), nullable=False),
        sa.Column('badge_number', sa.String(50), unique=True),
        sa.Column('department', sa.String(100)),
        sa.Column('phone_number', sa.String(20)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_super_admin', sa.Boolean, default=False),
        sa.Column('must_change_password', sa.Boolean, default=False),
        sa.Column('failed_login_attempts', sa.Integer, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('last_login_ip', sa.String(45)),
        sa.Column('preferences', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_email_role', 'users', ['email', 'role'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    # Continue with other tables...
    # [Add all other table creations here]

def downgrade():
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('feedback')
    op.drop_table('reports')
    op.drop_table('similarity_results')
    op.drop_table('feature_sets')
    op.drop_table('preprocessed_images')
    op.drop_table('forensic_images')
    op.drop_table('user_sessions')
    op.drop_table('password_resets')
    op.drop_table('ai_models')  
    op.drop_table('datasets')
    op.drop_table('system_config')
    op.drop_table('system_health')
    op.drop_table('users')
    
    # Drop ENUM types
    op.execute("DROP TYPE action_type_enum")
    op.execute("DROP TYPE feedback_priority_enum")
    op.execute("DROP TYPE feedback_type_enum")
    op.execute("DROP TYPE match_status_enum")
    op.execute("DROP TYPE match_confidence_enum")
    op.execute("DROP TYPE processing_status_enum")
    op.execute("DROP TYPE image_quality_enum")
    op.execute("DROP TYPE image_type_enum")
    op.execute("DROP TYPE user_role_enum")