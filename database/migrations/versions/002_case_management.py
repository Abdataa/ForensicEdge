"""Add Case Management tables and new audit_log action types

Revision ID: 002_case_management
Revises:     001_initial_schema
Create Date: 2025-12-01

What this migration does
-------------------------
1. Adds 7 new values to the action_type PostgreSQL ENUM
   (case_created, case_updated, case_deleted,
    case_evidence_linked, case_analysis_linked,
    case_report_linked, case_note_added, image_viewed)

2. Creates 2 new PostgreSQL ENUM types:
   - case_status   (OPEN, IN_PROGRESS, REVIEW, CLOSED)
   - case_priority (LOW, MEDIUM, HIGH)

3. Creates 5 new tables:
   - cases
   - case_evidence
   - case_analyses
   - case_reports
   - case_notes

Important notes on PostgreSQL ENUM alteration
----------------------------------------------
PostgreSQL does NOT support ALTER TYPE ... ADD VALUE inside a
transaction block (versions < 12 raise an error; >= 12 allows it
but with restrictions). Alembic wraps each migration in a transaction
by default. The workaround is to run the ALTER statements in a
separate transaction using op.execute() with a raw COMMIT/BEGIN,
OR set transaction=False for the migration (done here with
connection.execution_options(isolation_level="AUTOCOMMIT")).

This migration uses AUTOCOMMIT for the enum value additions only,
then re-enables transaction for the DDL (table creation).

Run with:
    cd backend
    alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa


# Alembic revision identifiers
revision  = "002_case_management"
down_revision = "001_initial_schema"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Add new values to the action_type ENUM
    # Must run outside a transaction (AUTOCOMMIT) in PostgreSQL.
    # ─────────────────────────────────────────────────────────────────────────
    connection = op.get_bind()
    connection.execution_options(isolation_level="AUTOCOMMIT")

    new_action_types = [
        "image_viewed",
        "case_created",
        "case_updated",
        "case_deleted",
        "case_evidence_linked",
        "case_analysis_linked",
        "case_report_linked",
        "case_note_added",
    ]
    for value in new_action_types:
        connection.execute(
            sa.text(
                f"ALTER TYPE action_type ADD VALUE IF NOT EXISTS '{value}'"
            )
        )

    # Restore normal transaction behaviour for table DDL
    connection.execution_options(isolation_level="READ COMMITTED")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Create case_status and case_priority ENUM types
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE IF NOT EXISTS case_status AS ENUM "
               "('OPEN', 'IN_PROGRESS', 'REVIEW', 'CLOSED')")
    op.execute("CREATE TYPE IF NOT EXISTS case_priority AS ENUM "
               "('LOW', 'MEDIUM', 'HIGH')")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: Create cases table
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "cases",
        sa.Column("id",          sa.Integer,                 primary_key=True, index=True),
        sa.Column("title",       sa.String(255),             nullable=False),
        sa.Column("description", sa.Text,                    nullable=True),
        sa.Column("created_by",  sa.Integer,
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status",   sa.Enum("OPEN","IN_PROGRESS","REVIEW","CLOSED",
                                      name="case_status",   create_type=False),
                  nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.Enum("LOW","MEDIUM","HIGH",
                                      name="case_priority", create_type=False),
                  nullable=False, server_default="MEDIUM"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cases_created_by",  "cases", ["created_by"])
    op.create_index("ix_cases_assigned_to", "cases", ["assigned_to"])
    op.create_index("ix_cases_status",      "cases", ["status"])

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: Create case_evidence table
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "case_evidence",
        sa.Column("id",       sa.Integer, primary_key=True, index=True),
        sa.Column("case_id",  sa.Integer,
                  sa.ForeignKey("cases.id", ondelete="CASCADE"),  nullable=False),
        sa.Column("image_id", sa.Integer,
                  sa.ForeignKey("forensic_images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linked_by", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.UniqueConstraint("case_id", "image_id", name="uq_case_evidence"),
    )
    op.create_index("ix_case_evidence_case_id",  "case_evidence", ["case_id"])
    op.create_index("ix_case_evidence_image_id", "case_evidence", ["image_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: Create case_analyses table
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "case_analyses",
        sa.Column("id",        sa.Integer, primary_key=True, index=True),
        sa.Column("case_id",   sa.Integer,
                  sa.ForeignKey("cases.id", ondelete="CASCADE"),           nullable=False),
        sa.Column("result_id", sa.Integer,
                  sa.ForeignKey("similarity_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at",  sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("case_id", "result_id", name="uq_case_analysis"),
    )
    op.create_index("ix_case_analyses_case_id",   "case_analyses", ["case_id"])
    op.create_index("ix_case_analyses_result_id", "case_analyses", ["result_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # Step 6: Create case_reports table
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "case_reports",
        sa.Column("id",        sa.Integer, primary_key=True, index=True),
        sa.Column("case_id",   sa.Integer,
                  sa.ForeignKey("cases.id",    ondelete="CASCADE"), nullable=False),
        sa.Column("report_id", sa.Integer,
                  sa.ForeignKey("reports.id",  ondelete="CASCADE"), nullable=False),
        sa.Column("added_at",  sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("case_id", "report_id", name="uq_case_report"),
    )
    op.create_index("ix_case_reports_case_id",   "case_reports", ["case_id"])
    op.create_index("ix_case_reports_report_id", "case_reports", ["report_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # Step 7: Create case_notes table
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "case_notes",
        sa.Column("id",        sa.Integer, primary_key=True, index=True),
        sa.Column("case_id",   sa.Integer,
                  sa.ForeignKey("cases.id",  ondelete="CASCADE"),  nullable=False),
        sa.Column("user_id",   sa.Integer,
                  sa.ForeignKey("users.id",  ondelete="SET NULL"), nullable=True),
        sa.Column("note_text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_notes_case_id", "case_notes", ["case_id"])
    op.create_index("ix_case_notes_user_id", "case_notes", ["user_id"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("case_notes")
    op.drop_table("case_reports")
    op.drop_table("case_analyses")
    op.drop_table("case_evidence")
    op.drop_table("cases")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS case_priority")
    op.execute("DROP TYPE IF EXISTS case_status")

    # Note: PostgreSQL does not support removing ENUM values.
    # The new action_type values (case_*, image_viewed) remain
    # in the enum after downgrade — they simply become unused.
    # This is safe and does not affect existing data.