"""Object pixel projection tests."""

import pytest

from cctv_lens_calc.domain.calculator import calculate
from cctv_lens_calc.domain.models import CalculateRequest, CameraParams, LensType, ObjectParams


def test_cola_can_pixels_close_up():
    req = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=5.37,
            sensor_height_mm=3.02,
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=2.8,
            lens_type=LensType.RECTILINEAR,
            distance_m=0.45,
        ),
        object=ObjectParams(object_id="cola_can", object_distance_m=0.45),
    )
    result = calculate(req)
    assert result.projection is not None
    assert result.projection.width_px == pytest.approx(146.8, rel=0.01)
    assert result.projection.height_px == pytest.approx(266.9, rel=0.01)
    assert result.projection.center_u_px == pytest.approx(960.0, abs=0.5)
    assert result.projection.center_v_px == pytest.approx(540.0, abs=0.5)


def test_projection_center_shifts_with_offset():
    req = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=5.37,
            sensor_height_mm=3.02,
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=2.8,
            distance_m=1.0,
        ),
        object=ObjectParams(
            object_id="cola_can",
            object_distance_m=1.0,
            object_offset_y_m=0.1,
            object_offset_z_m=0.05,
        ),
    )
    p = calculate(req).projection
    assert p is not None
    assert p.center_u_px > 1920 / 2
    assert p.center_v_px < 1080 / 2


def test_resolution_scales_pixel_projection():
    base = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=5.37,
            sensor_height_mm=3.02,
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=2.8,
            distance_m=1.0,
        ),
        object=ObjectParams(object_id="donut", object_distance_m=1.0),
    )
    hd = base.model_copy(
        update={
            "camera": base.camera.model_copy(
                update={"resolution_w": 3840, "resolution_h": 2160}
            )
        }
    )
    p1 = calculate(base).projection
    p2 = calculate(hd).projection
    assert p2.width_px == pytest.approx(p1.width_px * 2, rel=0.01)
    assert p2.height_px == pytest.approx(p1.height_px * 2, rel=0.01)


def test_api_calculate_schema(httpx_client):
    body = {
        "camera": {
            "sensor_width_mm": 4.8,
            "sensor_height_mm": 3.6,
            "resolution_w": 1920,
            "resolution_h": 1080,
            "focal_length_mm": 4.0,
            "lens_type": "rectilinear",
            "distance_m": 10.0,
        },
        "object": {"object_id": "donut", "object_distance_m": 1.0},
    }
    r = httpx_client.post("/api/calculate", json=body)
    assert r.status_code == 200
    data = r.json()
    for key in ("fov", "coverage", "density", "dori", "projection"):
        assert key in data
    assert data["fov"]["hfov_deg"] > 0
    assert data["density"]["ppm"] > 0
