"""FastAPI application for CameraCalculator."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cctv_lens_calc import __version__
from cctv_lens_calc.api.routes import router

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"
MODELS_DIR = Path("/app/models") if Path("/app/models").is_dir() else Path(__file__).resolve().parents[4] / "models"


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

    return app


app = create_app()
