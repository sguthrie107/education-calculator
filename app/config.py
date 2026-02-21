"""Application configuration."""
import os
from pathlib import Path

# Database
# Railway provides DATABASE_URL as postgres://, but SQLAlchemy requires postgresql://
_raw_db_url = os.getenv("DATABASE_URL", "sqlite:///education.db")
DATABASE_URL = _raw_db_url.replace("postgres://", "postgresql://", 1)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8001").split(",")

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# 529 Plan defaults
BASE_YEAR = 2026
MONTHLY_CONTRIBUTION = 200.00
INITIAL_INVESTMENT = 2500.00
MAX_CHILD_AGE = 20
