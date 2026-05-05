"""
backend/app/core/dependencies_ml_addition.py
─────────────────────────────────────────────
HOW TO WIRE THE NEW ML DEPENDENCY INTO YOUR EXISTING dependencies.py
─────────────────────────────────────────────────────────────────────

Your existing app/core/dependencies.py already has AdminUser.
Add the MlUser dependency below it — it is the same pattern but
allows both "ai_engineer" and "admin" roles.

─────────────────────────────────────────────────────────────────────
STEP 1 — Add MlUser to app/core/dependencies.py
─────────────────────────────────────────────────────────────────────

Find your existing AdminUser dependency (roughly):

    async def get_admin_user(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        return current_user

    AdminUser = Annotated[User, Depends(get_admin_user)]

Add this immediately after it:

    async def get_ml_user(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in ("admin", "ai_engineer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="AI Engineer or Admin access required.",
            )
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )
        return current_user

    MlUser = Annotated[User, Depends(get_ml_user)]

─────────────────────────────────────────────────────────────────────
STEP 2 — Register the ML models in app/db/base.py
─────────────────────────────────────────────────────────────────────

Open app/db/base.py (the file that imports all models so
Base.metadata.create_all sees them). Add one line:

    from app.models.ml import MlDataset, MlModelVersion, MlTrainingJob, MlEvaluation  # noqa: F401

The full file should look roughly like:

    from app.core.database import Base           # noqa: F401

    from app.models.user       import User           # noqa: F401
    from app.models.image      import Image          # noqa: F401
    from app.models.comparison import ComparisonResult  # noqa: F401
    from app.models.report     import Report         # noqa: F401
    from app.models.audit_log  import AuditLog       # noqa: F401
    from app.models.case       import Case           # noqa: F401
    # ── NEW ──
    from app.models.ml import MlDataset, MlModelVersion, MlTrainingJob, MlEvaluation  # noqa: F401

─────────────────────────────────────────────────────────────────────
STEP 3 — Register the router in app/main.py
─────────────────────────────────────────────────────────────────────

In main.py, add two lines:

    # At the top with the other router imports:
    from app.api.routes_ml import router as ml_router

    # In the "Routers" section with the other include_router calls:
    app.include_router(ml_router, prefix=PREFIX)

The complete router block should look like:

    app.include_router(auth_router,     prefix=PREFIX)
    app.include_router(upload_router,   prefix=PREFIX)
    app.include_router(compare_router,  prefix=PREFIX)
    app.include_router(report_router,   prefix=PREFIX)
    app.include_router(admin_router,    prefix=PREFIX)
    app.include_router(logs_router,     prefix=PREFIX)
    app.include_router(feedback_router, prefix=PREFIX)
    app.include_router(cases_router,    prefix=PREFIX)
    app.include_router(ml_router,       prefix=PREFIX)   # ← NEW

─────────────────────────────────────────────────────────────────────
STEP 4 — Add STORAGE_ROOT to app/core/config.py
─────────────────────────────────────────────────────────────────────

ml_service.py reads settings.STORAGE_ROOT for the file storage base.
If your config doesn't have it yet, add:

    STORAGE_ROOT: str = "storage"

─────────────────────────────────────────────────────────────────────
STEP 5 — (Optional) Add python-multipart to requirements
─────────────────────────────────────────────────────────────────────

The dataset upload endpoint uses multipart/form-data.
FastAPI needs python-multipart for this:

    pip install python-multipart

Add to requirements.txt:
    python-multipart>=0.0.9

─────────────────────────────────────────────────────────────────────
No database migrations needed for local dev
─────────────────────────────────────────────────────────────────────

Your lifespan already calls Base.metadata.create_all — once
app/db/base.py imports the ML models (Step 2), the four new tables
(ml_datasets, ml_model_versions, ml_training_jobs, ml_evaluations)
are created automatically on next server start.

For production, generate an Alembic migration instead:
    alembic revision --autogenerate -m "add ml tables"
    alembic upgrade head

─────────────────────────────────────────────────────────────────────
Inline MlUser dependency (copy this into dependencies.py directly)
─────────────────────────────────────────────────────────────────────
"""

# ── Copy the block below into app/core/dependencies.py ──────────────────────

from typing import Annotated

from fastapi import Depends, HTTPException, status

# These imports already exist in your dependencies.py:
# from app.models.user import User
# from app.core.security import get_current_user   (or equivalent)


async def get_ml_user(
    current_user,  # User = Depends(get_current_user)  ← add your actual dep here
) -> object:
    """
    Dependency: allow access to ai_engineer and admin roles only.

    Usage in route:
        current_user: MlUser   (imported from app.core.dependencies)
    """
    if current_user.role not in ("admin", "ai_engineer"):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "AI Engineer or Admin access required.",
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Account is deactivated.",
        )
    return current_user


# Wire this as an Annotated type in your dependencies.py:
# MlUser = Annotated[User, Depends(get_ml_user)]