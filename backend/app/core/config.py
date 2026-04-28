"""
backend/app/core/config.py
---------------------------
Central settings for the ForensicEdge FastAPI backend.

All values are read from the .env file (or environment variables) using
pydantic-settings.  Nothing is hardcoded here — secrets never appear in
source code or git history.

Usage
-----
    from app.core.config import settings

    # then access any value:
    settings.DATABASE_URL
    settings.SECRET_KEY
    settings.UPLOAD_DIR

.env file
---------
Copy .env.example → .env and fill in real values.
The .env file is already listed in .gitignore — never commit it.

Dependencies
------------
    pip install pydantic-settings python-dotenv
"""

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings.

    Pydantic-settings reads these from environment variables or the .env
    file.  Field names are matched case-insensitively.  If a required field
    is missing from both .env and the environment, FastAPI will raise a
    clear ValidationError at startup — not silently later.
    """

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME:     str = "ForensicEdge"
    DEBUG:        bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # PostgreSQL database
    # ------------------------------------------------------------------
    # Individual fields (used to assemble the URL)
    POSTGRES_USER:     str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST:     str = "localhost"
    POSTGRES_PORT:     int = 5432
    POSTGRES_DB:       str = "forensic_edge"

    # Async URL — used by SQLAlchemy async engine (asyncpg driver)
    # Assembled automatically from the individual fields above.
    # Can also be set directly in .env to override.
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    # Sync URL — used only for Alembic migrations (not for app runtime)
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    # ------------------------------------------------------------------
    # JWT / Security
    # ------------------------------------------------------------------
    # Generate a strong key with:  openssl rand -hex 32
    SECRET_KEY:                  str
    ALGORITHM:                   str  = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = 60    # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS:   int  = 7     # 7 days

    # ------------------------------------------------------------------
    # Storage — must match folder structure in project root
    # ------------------------------------------------------------------
    UPLOAD_DIR:  Path = Path("storage/uploads")
    REPORTS_DIR: Path = Path("storage/reports")
    LOGS_DIR:    Path = Path("storage/logs")

    # Max upload file size in bytes (10 MB default)
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    # Allowed image extensions for forensic evidence uploads
    ALLOWED_IMAGE_EXTENSIONS: list[str] = [".bmp", ".png", ".jpg", ".jpeg"]

    # ------------------------------------------------------------------
    # AI Engine
    # ------------------------------------------------------------------
    # Path to best_model.pth produced by train_siamese.py
    MODEL_WEIGHTS_PATH: Path = Path("ai_engine/models/weights/fingerprint_model_weights/best_model.pth")
    EMBEDDING_DIM:      int  = 256      # must match training config

    # Similarity thresholds — tune via experiments/threshold_experiment.py
    MATCH_THRESHOLD:    float = 85.0    # >= this → "MATCH"
    POSSIBLE_THRESHOLD: float = 60.0    # >= this → "POSSIBLE MATCH"

    #---------------------
    # First admin bootstrap (used only on first startup)
    FIRST_ADMIN_EMAIL:    str | None = None
    FIRST_ADMIN_PASSWORD: str | None = None

    # ------------------------------------------------------------------
    # CORS — origins allowed to call the API
    # During development: include localhost frontend ports
    # In production: restrict to your actual domain
    # ------------------------------------------------------------------
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",    # Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # ------------------------------------------------------------------
    # Pydantic-settings config
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file         = ".env",
        env_file_encoding= "utf-8",
        case_sensitive   = False,    # POSTGRES_USER == postgres_user
        extra            = "ignore", # ignore unknown .env vars silently
    )

    def create_storage_dirs(self) -> None:
        """
        Create storage directories if they don't exist.
        Called from main.py lifespan at application startup.
        """
        for directory in [self.UPLOAD_DIR, self.REPORTS_DIR, self.LOGS_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Singleton — instantiated once, imported everywhere
# ---------------------------------------------------------------------------
# @lru_cache ensures Settings() is only constructed once per process.
# Without this, every import would re-read and re-validate the .env file.

@lru_cache
def get_settings() -> Settings:
    return Settings()


# Module-level convenience alias
# Usage:  from app.core.config import settings
settings: Settings = get_settings()