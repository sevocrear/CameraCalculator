"""FastAPI application for CameraCalculator."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from cctv_lens_calc import __version__
from cctv_lens_calc.api.routes import router

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


def _resolve_models_dir() -> Path:
    """Resolve bundled models in source, wheel, and container executions."""
    configured = os.environ.get("MODELS_DIR")
    if configured:
        return Path(configured)
    candidates = (
        Path.cwd() / "models",
        Path(__file__).resolve().parents[3] / "models",
    )
    return next((path for path in candidates if path.is_dir()), candidates[0])


MODELS_DIR = _resolve_models_dir()


def create_app() -> FastAPI:
    """Build and configure FastAPI application."""
    app = FastAPI(
        title="CameraCalculator",
        version=__version__,
        description="Camera FOV, pixel density, and object projection calculator",
    )
    app.include_router(router)

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    if MODELS_DIR.is_dir():
        app.mount("/models", StaticFiles(directory=str(MODELS_DIR)), name="models")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    return app


app = create_app()
