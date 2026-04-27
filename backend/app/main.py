# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_auth
from core.database import engine, Base

# Create tables (for development)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ForensicEdge API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(routes_auth.router, prefix="/api/auth", tags=["Authentication"])

@app.get("/")
def root():
    return {"message": "ForensicEdge API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}