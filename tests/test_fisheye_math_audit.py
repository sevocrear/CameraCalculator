"""Fisheye math audit: Bob Atkins equidistant, DORI, PPM/GSD consistency."""

import math

import pytest

from cctv_lens_calc.domain import dori, fisheye, pinhole
from cctv_lens_calc.domain.calculator import calculate
from cctv_lens_calc.domain.models import CalculateRequest, CameraParams, LensType, ObjectParams


def test_bob_atkins_equidistant_hfov_formula():
    """FOV (equidistant) = (frame_size / f) * 57.3 — Bob Atkins."""
    for sensor_w, nominal in ((5.27, 160.0), (7.18, 180.0)):
        f = fisheye.effective_focal_from_fov(sensor_w, nominal)
        hfov = fisheye.fov_deg(sensor_w, f)
        bob = (sensor_w / f) * 57.3
        assert hfov == pytest.approx(nominal, abs=0.05)
        assert hfov == pytest.approx(bob, abs=0.05)


def test_bob_atkins_rectilinear_hfov_formula():
    """FOV (rectilinear) = 2 * atan(frame / (2f)) in degrees."""
    sensor_w, f = 4.8, 4.0
    expected = math.degrees(2.0 * math.atan(sensor_w / (2.0 * f)))
    assert pinhole.fov_deg(sensor_w, f) == pytest.approx(expected, rel=1e-9)


def test_fisheye_coverage_edge_ray_tan_model():
    """Scene width at Z uses perpendicular-plane intercept of edge ray (no cap)."""
    sensor_w = 5.27
    f = fisheye.effective_focal_from_fov(sensor_w, 120.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    assert hfov < 150.0
    z = 0.4
    theta = math.radians(hfov / 2.0)
    expected = 2.0 * z * math.tan(theta)
    assert fisheye.coverage_m(hfov, z) == pytest.approx(expected, rel=1e-9)


def test_fisheye_wide_hfov_coverage_uses_edge_ray_intersection():
    sensor_w = 5.27
    f = fisheye.effective_focal_from_fov(sensor_w, 160.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    expected = 2.0 * 0.4 * math.tan(math.radians(80.0))
    assert fisheye.coverage_m(hfov, 0.4) == pytest.approx(expected, rel=1e-9)


def test_fisheye_coverage_has_no_artificial_discontinuity_at_150_degrees():
    below = fisheye.coverage_m(149.999, 1.0)
    at_boundary = fisheye.coverage_m(150.0, 1.0)
    assert below is not None
    assert at_boundary is not None
    assert at_boundary == pytest.approx(below, rel=1e-4)


def test_fisheye_180_forward_plane_coverage_is_unbounded():
    sensor_w = 7.18
    f = fisheye.effective_focal_from_fov(sensor_w, 180.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    for z in (0.4, 5.0, 7.4):
        assert fisheye.coverage_m(hfov, z) is None


def test_fisheye_dori_shorter_than_pinhole_for_wide_uncapped():
    """Uncapped equidistant: pinhole DORI overestimates ident range vs real coverage."""
    res, sensor_w = 1920, 5.27
    f = fisheye.effective_focal_from_fov(sensor_w, 120.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    cov_per_m = fisheye.coverage_m(hfov, 1.0)
    d_correct = dori.dori_distances_from_coverage(res, cov_per_m)
    d_pinhole = dori.dori_distances(res, sensor_w, f)
    assert d_correct["identification_m"] < d_pinhole["identification_m"]


def test_calculator_fisheye_180_marks_plane_metrics_unavailable():
    req = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=7.18,
            sensor_height_mm=4.04,
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=1.4,
            lens_type=LensType.FISHEYE_EQUIDISTANT,
            fisheye_fov_deg=180.0,
            distance_m=5.0,
        ),
        object=ObjectParams(object_id="person", object_distance_m=5.0),
    )
    r = calculate(req)
    assert r.coverage.width_m is None
    assert r.density.ppm is None
    assert r.density.gsd_mm_per_px is None
    assert r.dori.identification_m is None
    assert r.dori.detection_m is None
    assert r.warnings


def test_fisheye_equidistant_projection_center_matches_pinhole_small_angle():
    """SkyEngine/OpenCV equidistant: r = f*theta; on-axis ≈ pinhole."""
    from cctv_lens_calc.domain.models import LensType
    from cctv_lens_calc.domain.projection import project_point_px

    kwargs = dict(
        sensor_width_mm=5.37,
        sensor_height_mm=3.02,
        focal_length_mm=2.8,
        resolution_w=1920,
        resolution_h=1080,
    )
    for x, y, z in ((0.0, 0.0, 2.0), (0.05, 0.02, 1.5)):
        pin = project_point_px(x, y, z, lens_type=LensType.RECTILINEAR, **kwargs)
        fish = project_point_px(x, y, z, lens_type=LensType.FISHEYE_EQUIDISTANT, **kwargs)
        assert fish[0] == pytest.approx(pin[0], rel=0.02)
        assert fish[1] == pytest.approx(pin[1], rel=0.02)


def test_fisheye_projection_is_radial_off_axis():
    """A diagonal ray must follow the standard radial equidistant mapping."""
    from cctv_lens_calc.domain.projection import project_point_px

    sensor_w, sensor_h = 5.37, 3.02
    resolution_w, resolution_h = 1920, 1080
    focal = 2.0
    x = y = z = 1.0
    u, v = project_point_px(
        x,
        y,
        z,
        sensor_width_mm=sensor_w,
        sensor_height_mm=sensor_h,
        focal_length_mm=focal,
        resolution_w=resolution_w,
        resolution_h=resolution_h,
        lens_type=LensType.FISHEYE_EQUIDISTANT,
    )
    radial_distance = math.hypot(x, y)
    radius_mm = focal * math.atan2(radial_distance, z)
    expected_sensor_axis_mm = radius_mm / math.sqrt(2.0)
    assert u == pytest.approx(
        resolution_w / 2 + expected_sensor_axis_mm / (sensor_w / resolution_w)
    )
    assert v == pytest.approx(
        resolution_h / 2 - expected_sensor_axis_mm / (sensor_h / resolution_h)
    )


def test_fisheye_projected_rect_includes_axis_edge_extrema():
    """A centered rectangle reaches its widest points at edge midpoints."""
    from cctv_lens_calc.domain.projection import project_box_bbox_px

    params = {
        "sensor_width_mm": 7.18,
        "sensor_height_mm": 4.04,
        "focal_length_mm": 2.2,
        "resolution_w": 1920,
        "resolution_h": 1080,
        "lens_type": LensType.FISHEYE_EQUIDISTANT,
    }
    bbox = project_box_bbox_px(0.0, 0.0, 1.0, 0.6, 0.4, 0.0, **params)
    expected_w, expected_h = fisheye.object_pixels(
        0.6,
        0.4,
        1.0,
        params["sensor_width_mm"],
        params["sensor_height_mm"],
        params["focal_length_mm"],
        params["resolution_w"],
        params["resolution_h"],
    )
    assert bbox[2] - bbox[0] == pytest.approx(expected_w)
    assert bbox[3] - bbox[1] == pytest.approx(expected_h)
