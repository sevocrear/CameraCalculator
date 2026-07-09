"""Golden case regression tests from fixtures."""

import json
from pathlib import Path

import pytest

from cctv_lens_calc.domain.calculator import calculate
from cctv_lens_calc.domain.models import CalculateRequest, CameraParams, LensType, ObjectParams

FIXTURES = Path(__file__).parent / "fixtures" / "golden_cases.json"


def _load_cases():
    with FIXTURES.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_golden_case(case):
    cam_data = case["camera"]
    obj_data = case["object"]
    expected = case["expected"]
    tol = expected.get("tolerance_pct", 1.0) / 100.0

    lens_type = LensType(cam_data["lens_type"])
    req = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=cam_data["sensor_width_mm"],
            sensor_height_mm=cam_data["sensor_height_mm"],
            resolution_w=cam_data["resolution_w"],
            resolution_h=cam_data["resolution_h"],
            focal_length_mm=cam_data["focal_length_mm"],
            lens_type=lens_type,
            fisheye_fov_deg=cam_data.get("fisheye_fov_deg"),
            distance_m=cam_data["distance_m"],
            mount_height_m=cam_data.get("mount_height_m", 2.5),
        ),
        object=ObjectParams(
            object_id=obj_data["object_id"],
            object_distance_m=obj_data.get("object_distance_m"),
        ),
    )
    result = calculate(req)

    if "hfov_deg" in expected:
        assert result.fov.hfov_deg == pytest.approx(expected["hfov_deg"], rel=tol)
    if "coverage_width_m" in expected:
        assert result.coverage.width_m == pytest.approx(
            expected["coverage_width_m"], rel=tol
        )
    if "ppm" in expected:
        assert result.density.ppm == pytest.approx(expected["ppm"], rel=tol)
    if "projection_width_px" in expected:
        assert result.projection.width_px == pytest.approx(
            expected["projection_width_px"], rel=tol
        )
    if "projection_height_px" in expected:
        assert result.projection.height_px == pytest.approx(
            expected["projection_height_px"], rel=tol
        )
