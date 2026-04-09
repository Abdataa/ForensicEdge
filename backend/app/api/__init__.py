"""
backend/app/api/__init__.py
-----------------------------
Aggregate all API routers.
"""

from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_images import router as images_router
from app.api.routes_similarity import router as similarity_router
from app.api.routes_feedback import router as feedback_router
from app.api.routes_reports import router as reports_router
from app.api.routes_admin_users import router as admin_users_router
from app.api.routes_logs import router as logs_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(images_router)
api_router.include_router(similarity_router)
api_router.include_router(feedback_router)
api_router.include_router(reports_router)
api_router.include_router(admin_users_router)
api_router.include_router(logs_router)