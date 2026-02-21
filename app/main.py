"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from .database import init_db
from .routes import dashboard, projections, balances
from .auth import BasicAuthMiddleware

BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Family Education Dashboard",
        description="Track and project education savings for up to 3 children with household loan payoff overlay",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Enforce HTTP Basic Auth on all routes
    app.add_middleware(BasicAuthMiddleware)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(dashboard.router, tags=["dashboard"])
    app.include_router(projections.router, tags=["projections"])
    app.include_router(balances.router, tags=["balances"])

    return app


app = create_app()


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}
