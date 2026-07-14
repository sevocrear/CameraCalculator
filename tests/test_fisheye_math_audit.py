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


def test_fisheye_wide_hfov_coverage_capped_at_2z():
    sensor_w = 5.27
    f = fisheye.effective_focal_from_fov(sensor_w, 160.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    assert fisheye.coverage_m(hfov, 0.4) == pytest.approx(0.8, rel=1e-9)


def test_fisheye_180_coverage_capped_at_2z():
    sensor_w = 7.18
    f = fisheye.effective_focal_from_fov(sensor_w, 180.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    for z in (0.4, 5.0, 7.4):
        assert fisheye.coverage_m(hfov, z) == pytest.approx(2.0 * z, rel=1e-9)


def test_fisheye_dori_shorter_than_pinhole_for_wide_uncapped():
    """Uncapped equidistant: pinhole DORI overestimates ident range vs real coverage."""
    res, sensor_w = 1920, 5.27
    f = fisheye.effective_focal_from_fov(sensor_w, 120.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    cov_per_m = fisheye.coverage_m(hfov, 1.0)
    d_correct = dori.dori_distances_from_coverage(res, cov_per_m)
    d_pinhole = dori.dori_distances(res, sensor_w, f)
    assert d_correct["identification_m"] < d_pinhole["identification_m"]


def test_fisheye_180_dori_identification_distance():
    """180° fisheye: W=2Z → ident @ res/(250*2)."""
    res = 1920
    sensor_w = 7.18
    f = fisheye.effective_focal_from_fov(sensor_w, 180.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    cov_per_m = fisheye.coverage_m(hfov, 1.0)
    d = dori.dori_distances_from_coverage(res, cov_per_m)
    assert cov_per_m == pytest.approx(2.0, rel=1e-9)
    assert d["identification_m"] == pytest.approx(res / 500.0, rel=1e-9)


def test_calculator_fisheye_ppm_gsd_dori_consistent():
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
    assert r.coverage.width_m == pytest.approx(10.0, rel=1e-9)
    assert r.density.ppm == pytest.approx(192.0, rel=1e-9)
    assert r.density.gsd_mm_per_px == pytest.approx(1000.0 / 192.0, abs=0.001)
    assert r.dori.identification_m == pytest.approx(3.84, rel=1e-3)
    assert r.dori.detection_m == pytest.approx(38.4, rel=1e-3)


def test_fisheye_equidistant_projection_center_matches_pinhole_small_angle():
    """SkyEngine/OpenCV equidistant: r = f*theta; on-axis ≈ pinhole."""
    from cctv_lens_calc.domain.projection import project_point_px
    from cctv_lens_calc.domain.models import LensType

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
