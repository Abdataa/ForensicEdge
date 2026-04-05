# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine, Base, test_connection
from core.config import settings
import logging
from app.api import routes_cases, routes_upload, routes_feedback, routes_auth, routes_admin, routes_logs, routes_compare, routes_reports
from models import user, forensic_image, dataset, feature_set, model_version, similarity_result, case, case_evidence, report, feedback
from models.preprocessed_image import PreprocessedImage
from models.audit_log import AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ForensicEdge API",
    description="AI-Powered Forensic Analysis System",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting ForensicEdge API...")
    
    # Test database connection
    if not test_connection():
        logger.error("Failed to connect to database. Exiting...")
        exit(1)
    
    # Create tables (for development only)
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tables created successfully!")

@app.get("/")
async def root():
    return {
        "message": "Welcome to ForensicEdge API",
        "version": "1.0.0",
        "status": "operational",
        "database": "connected"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "api": "operational"
    }

app.include_router(routes_cases.router)
app.include_router(routes_upload.router)
app.include_router(routes_feedback.router)
app.include_router(routes_auth.router)
app.include_router(routes_admin.router)
app.include_router(routes_logs.router)
app.include_router(routes_compare.router)
app.include_router(routes_reports.router)
