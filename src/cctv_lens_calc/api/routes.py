"""API routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from cctv_lens_calc import __version__
from cctv_lens_calc.domain.calculator import calculate
from cctv_lens_calc.domain.models import CalculateRequest, CalculateResponse, LensType
from cctv_lens_calc.domain.presets import (
    CAMERA_PRESETS,
    CV_THRESHOLDS,
    SENSOR_PRESETS,
    camera_to_params,
)
from cctv_lens_calc.domain.reference_objects import list_objects

router = APIRouter()
STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


@router.get("/health")
def health() -> JSONResponse:
    """Liveness and readiness probe."""
    index_path = STATIC_DIR / "index.html"
    static_ok = index_path.is_file()
    presets_ok = len(CAMERA_PRESETS) > 0 and len(SENSOR_PRESETS) > 0
    checks = {"static_index": static_ok, "presets_loaded": presets_ok}
    ok = all(checks.values())
    body = {"status": "ok" if ok else "degraded", "version": __version__, "checks": checks}
    return JSONResponse(content=body, status_code=200 if ok else 503)


@router.get("/")
def index() -> FileResponse:
    """Serve main UI."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@router.post("/api/calculate", response_model=CalculateResponse)
def api_calculate(request: CalculateRequest) -> CalculateResponse:
    """Calculate FOV, coverage, density, and object projection."""
    return calculate(request)


@router.get("/api/presets/sensors")
def presets_sensors() -> list[dict]:
    """List sensor format presets."""
    return [
        {
            "id": s.id,
            "label": s.label,
            "width_mm": s.width_mm,
            "height_mm": s.height_mm,
            "diagonal_mm": s.diagonal_mm,
            "aspect": s.aspect,
        }
        for s in SENSOR_PRESETS.values()
    ]


@router.get("/api/presets/cameras")
def presets_cameras() -> list[dict]:
    """List camera presets with expanded parameters."""
    result = []
    for cam in CAMERA_PRESETS.values():
        params = camera_to_params(cam.id)
        result.append(
            {
                "id": cam.id,
                "label": cam.label,
                "sensor_id": cam.sensor_id,
                "resolution_w": cam.resolution_w,
                "resolution_h": cam.resolution_h,
                "focal_length_mm": cam.focal_length_mm,
                "lens_type": cam.lens_type.value,
                "fisheye_fov_deg": cam.fisheye_fov_deg,
                "datasheet_url": cam.datasheet_url,
                "expanded": params,
            }
        )
    return result


@router.get("/api/presets/objects")
def presets_objects() -> list[dict]:
    """List reference objects."""
    return [
        {
            "id": o.id,
            "label": o.label,
            "width_m": o.width_m,
            "height_m": o.height_m,
            "depth_m": o.depth_m,
            "cv_threshold_px": o.cv_threshold_px,
            "orientation": o.orientation.value,
            "model_offset_y_m": o.model_offset_y_m,
            "model_offset_z_m": o.model_offset_z_m,
            "model_mesh_offset_x_m": o.model_mesh_offset_x_m,
            "model_mesh_offset_y_m": o.model_mesh_offset_y_m,
            "model_mesh_offset_z_m": o.model_mesh_offset_z_m,
            "model_rotation_xyz": list(o.model_rotation_xyz),
            "model_scale_mul": o.model_scale_mul,
        }
        for o in list_objects()
    ]


@router.get("/api/presets/cv_thresholds")
def presets_cv_thresholds() -> dict:
    """CV pipeline pixel thresholds."""
    return CV_THRESHOLDS
