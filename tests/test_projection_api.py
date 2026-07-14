"""API projection tests — finite math, edge FOV, no circular self-checks."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from cctv_lens_calc.domain import fisheye, pinhole
from cctv_lens_calc.domain.calculator import calculate
from cctv_lens_calc.domain.models import CalculateRequest, CameraParams, LensType, ObjectParams
from cctv_lens_calc.domain.reference_objects import REFERENCE_OBJECTS

FIXTURE = Path(__file__).parent / "fixtures" / "projection_matrix.json"
MATRIX = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _build_request(cfg: dict, object_id: str) -> CalculateRequest:
    lt = LensType(cfg["lens_type"])
    if lt == LensType.FISHEYE_EQUIDISTANT:
        f_mm = fisheye.effective_focal_from_fov(cfg["sensor_width_mm"], cfg["hfov_deg"])
        fisheye_fov = cfg["hfov_deg"]
    else:
        from cctv_lens_calc.domain.projection import rectilinear_focal_from_hfov

        f_mm = rectilinear_focal_from_hfov(cfg["sensor_width_mm"], cfg["hfov_deg"])
        fisheye_fov = None
    return CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=cfg["sensor_width_mm"],
            sensor_height_mm=cfg["sensor_height_mm"],
            resolution_w=cfg["resolution_w"],
            resolution_h=cfg["resolution_h"],
            focal_length_mm=f_mm,
            lens_type=lt,
            fisheye_fov_deg=fisheye_fov,
            distance_m=cfg["distance_m"],
            mount_height_m=2.5,
        ),
        object=ObjectParams(
            object_id=object_id,
            object_distance_m=cfg["object_distance_m"],
            object_offset_z_m=cfg.get("object_offset_z_m", 0.0),
            object_offset_y_m=cfg.get("object_offset_y_m", 0.0),
        ),
    )


def test_fisheye_180_coverage_and_density_finite():
    """Regression: 180° fisheye must not overflow coverage/PPM."""
    cfg = next(c for c in MATRIX if c["id"] == "F180")
    result = calculate(_build_request(cfg, "cola_can"))
    assert math.isfinite(result.coverage.width_m)
    assert math.isfinite(result.coverage.height_m)
    assert result.coverage.width_m <= 2.0 * cfg["distance_m"] + 0.01
    assert result.density.ppm > 0
    assert result.density.ppm < 1e6


def test_fisheye_180_focal_not_zero():
    f = fisheye.effective_focal_from_fov(7.18, 180.0)
    assert f > 1.0
    assert f == pytest.approx(2.2855, abs=0.001)


def test_fisheye_179_vs_180_basket_smaller_at_180():
    cfg179 = next(c for c in MATRIX if c["id"] == "F179")
    cfg180 = next(c for c in MATRIX if c["id"] == "F180")
    p179 = calculate(_build_request(cfg179, "basket")).projection
    p180 = calculate(_build_request(cfg180, "basket")).projection
    assert p179.width_px > p180.width_px
    assert abs(p179.width_px - p180.width_px) > 1.0


def test_basket_f180_fits_frame():
    cfg = next(c for c in MATRIX if c["id"] == "F180")
    p = calculate(_build_request(cfg, "basket")).projection
    left = p.center_u_px - p.width_px / 2
    top = p.center_v_px - p.height_px / 2
    right = p.center_u_px + p.width_px / 2
    bottom = p.center_v_px + p.height_px / 2
    assert left >= 0
    assert top >= 0
    assert right <= cfg["resolution_w"]
    assert bottom <= cfg["resolution_h"]


@pytest.mark.parametrize(
    "cfg_id,object_id",
    [
        ("R60", "donut"),
        ("R60", "cola_can"),
        ("F180", "cola_can"),
        ("F180", "basket"),
        ("F90", "basket"),
        ("R90_OFF", "basket"),
    ],
)
def test_projection_positive_pixels(cfg_id, object_id):
    cfg = next(c for c in MATRIX if c["id"] == cfg_id)
    p = calculate(_build_request(cfg, object_id)).projection
    assert p is not None
    assert p.width_px > 0
    assert p.height_px > 0
    assert 0 <= p.center_u_px <= cfg["resolution_w"]
    assert 0 <= p.center_v_px <= cfg["resolution_h"]


def test_pinhole_safe_tan_at_180():
    cov = pinhole.coverage_m(180.0, 3.0)
    assert math.isfinite(cov)
    assert cov < 1e6


def test_all_reference_objects_have_dims():
    for oid, ref in REFERENCE_OBJECTS.items():
        assert ref.width_m > 0
        assert ref.height_m > 0
