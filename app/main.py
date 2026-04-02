"""FastAPI application factory."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .auth import BasicAuthMiddleware
from .database import init_db
from .routes import balances, dashboard, projections
from .security_headers import SecurityHeadersMiddleware

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    try:
        init_db()
    except Exception:
        log.exception(
            "Database initialisation failed — app will start without a seeded DB. "
            "Check DATABASE_URL and PostgreSQL connectivity."
        )
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Family Education Dashboard",
        description="Track and project education savings for up to 3 children with household loan payoff overlay",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BasicAuthMiddleware)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(dashboard.router, tags=["dashboard"])
    app.include_router(projections.router, tags=["projections"])
    app.include_router(balances.router, tags=["balances"])

    @app.get("/health", include_in_schema=False)
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
