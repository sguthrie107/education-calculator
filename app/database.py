"""Database configuration and session management."""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import json
from pathlib import Path

from .config import DATABASE_URL
from .models import Base, Child

log = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_default_children():
    """Load default children from children.json into the database."""
    db = SessionLocal()
    try:
        children_file = Path(__file__).parent.parent / "data" / "children.json"

        if not children_file.exists():
            return

        with open(children_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for child_data in data.get("children", []):
            existing = db.query(Child).filter(Child.name == child_data["name"]).first()
            if not existing:
                new_child = Child(name=child_data["name"])
                db.add(new_child)

        db.commit()
    except Exception:
        db.rollback()
        log.exception("Error seeding children")
    finally:
        db.close()


def init_db():
    """Initialize database tables and seed default data."""
    Base.metadata.create_all(bind=engine)
    seed_default_children()


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
