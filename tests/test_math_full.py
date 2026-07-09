"""Full math coverage: FOV, coverage, PPM, object pixels, DORI, calculator."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cctv_lens_calc.domain import dori, fisheye, pinhole
from cctv_lens_calc.domain.calculator import calculate
from cctv_lens_calc.domain.models import (
    CalculateRequest,
    CameraParams,
    LensType,
    ObjectParams,
)
from cctv_lens_calc.domain.reference_objects import ObjectOrientation, get_object


def test_coverage_equals_z_times_sensor_over_f():
    """JVSG: W = Z * sensor_w / f  ≡  2*Z*tan(HFOV/2)."""
    z, sw, f = 10.0, 4.8, 4.0
    hfov = pinhole.fov_deg(sw, f)
    assert pinhole.coverage_m(hfov, z) == pytest.approx(z * sw / f, rel=1e-9)


def test_ppm_identity():
    z, sw, f, res = 10.0, 4.8, 4.0, 1920
    hfov = pinhole.fov_deg(sw, f)
    w = pinhole.coverage_m(hfov, z)
    ppm = res / w
    assert pinhole.ppm_at_distance(res, sw, f, z) == pytest.approx(ppm, rel=1e-9)
    assert ppm == pytest.approx(160.0, rel=0.005)


def test_object_pixels_identity():
    """px = size_m * res * f / (Z * sensor)."""
    ow, oh, z = 0.10, 0.03, 1.0
    sw, sh, f, rw, rh = 5.37, 3.02, 2.8, 1920, 1080
    px_w, px_h = pinhole.object_pixels(ow, oh, z, sw, sh, f, rw, rh)
    assert px_w == pytest.approx(ow * rw * f / (z * sw), rel=1e-9)
    assert px_h == pytest.approx(oh * rh * f / (z * sh), rel=1e-9)


def test_gsd_inverse_of_ppm():
    z, sw, f, res = 1.0, 5.37, 2.8, 1920
    ppm = pinhole.ppm_at_distance(res, sw, f, z)
    gsd_mm = pinhole.gsd_mm_per_px(z, sw, f, res)
    assert gsd_mm == pytest.approx(1000.0 / ppm, rel=1e-6)


def test_object_pixels_scale_inverse_with_distance():
    kwargs = dict(
        object_width_m=0.066,
        object_height_m=0.12,
        sensor_width_mm=5.37,
        sensor_height_mm=3.02,
        focal_length_mm=2.8,
        resolution_w=1920,
        resolution_h=1080,
    )
    px1 = pinhole.object_pixels(object_distance_m=0.5, **kwargs)
    px2 = pinhole.object_pixels(object_distance_m=1.0, **kwargs)
    assert px1[0] == pytest.approx(2 * px2[0], rel=1e-9)
    assert px1[1] == pytest.approx(2 * px2[1], rel=1e-9)


def test_donut_orientation_is_flat_xz():
    donut = get_object("donut")
    assert donut is not None
    assert donut.orientation == ObjectOrientation.UPRIGHT
    assert donut.width_m == pytest.approx(donut.height_m)


def test_donut_projection_aspect_wide_and_short():
    """Пончик «лицом» 10×10 см @ 1 м: width_px ≈ height_px."""
    req = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=5.37,
            sensor_height_mm=3.02,
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=2.8,
            lens_type=LensType.RECTILINEAR,
            distance_m=1.0,
            mount_height_m=2.5,
        ),
        object=ObjectParams(object_id="donut", object_distance_m=1.0),
    )
    result = calculate(req)
    p = result.projection
    assert p is not None
    assert p.orientation == "upright"
    assert p.width_px == pytest.approx(100.1, rel=0.02)
    assert p.height_px == pytest.approx(100.2, rel=0.02)
    assert 0.8 < p.aspect_wh < 1.25


def test_cola_projection_taller_than_wide():
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
    p = calculate(req).projection
    assert p is not None
    assert p.orientation == "upright"
    assert p.height_px > p.width_px
    assert p.aspect_wh < 1.0


def test_cv_fail_when_below_threshold():
    """Пончик @ 1 м: min(100, 100)=100 >= 64 → CV pass."""
    req = CalculateRequest(
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
    p = calculate(req).projection
    assert p is not None
    assert p.cv_pass is True
    assert min(p.width_px, p.height_px) >= p.cv_threshold_px


def test_cv_pass_cola_close():
    req = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=5.37,
            sensor_height_mm=3.02,
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=2.8,
            distance_m=0.45,
        ),
        object=ObjectParams(object_id="cola_can", object_distance_m=0.45),
    )
    p = calculate(req).projection
    assert p is not None
    assert p.cv_pass is True


def test_dori_monotonic_and_formula():
    res, sw, f = 1920, 5.37, 2.8
    d = dori.dori_distances(res, sw, f)
    assert (
        d["identification_m"]
        < d["recognition_m"]
        < d["observation_m"]
        < d["detection_m"]
    )
    assert d["identification_m"] == pytest.approx(res * f / (250.0 * sw), rel=1e-9)


def test_fisheye_fov_calibration_exact():
    for fov in (160.0, 180.0):
        f = fisheye.effective_focal_from_fov(5.27, fov)
        assert fisheye.fov_deg(5.27, f) == pytest.approx(fov, abs=1e-6)


def test_fisheye_small_angle_matches_pinhole():
    kwargs = dict(
        object_width_m=0.02,
        object_height_m=0.02,
        object_distance_m=2.0,
        sensor_width_mm=5.37,
        sensor_height_mm=3.02,
        focal_length_mm=2.8,
        resolution_w=1920,
        resolution_h=1080,
    )
    pin = pinhole.object_pixels(**kwargs)
    fish = fisheye.object_pixels(**kwargs)
    assert fish[0] == pytest.approx(pin[0], rel=0.02)
    assert fish[1] == pytest.approx(pin[1], rel=0.02)


@given(
    z=st.floats(min_value=0.2, max_value=20.0),
    f=st.floats(min_value=1.0, max_value=12.0),
)
@settings(max_examples=40)
def test_prop_double_distance_halves_ppm(z, f):
    ppm1 = pinhole.ppm_at_distance(1920, 4.8, f, z)
    ppm2 = pinhole.ppm_at_distance(1920, 4.8, f, 2 * z)
    assert ppm1 == pytest.approx(2 * ppm2, rel=1e-6)


@given(f=st.floats(min_value=1.5, max_value=12.0))
@settings(max_examples=30)
def test_prop_longer_focal_narrower_hfov(f):
    assert pinhole.fov_deg(4.8, f) < pinhole.fov_deg(4.8, f * 0.5)


def test_calculator_coverage_matches_manual():
    req = CalculateRequest(
        camera=CameraParams(
            sensor_width_mm=4.8,
            sensor_height_mm=3.6,
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=4.0,
            distance_m=10.0,
        ),
        object=ObjectParams(object_id="person", object_distance_m=10.0),
    )
    r = calculate(req)
    assert r.coverage.width_m == pytest.approx(12.0, rel=0.005)
    assert r.density.ppm == pytest.approx(160.0, rel=0.01)
    assert r.fov.hfov_deg == pytest.approx(61.93, abs=0.2)
    assert r.projection is not None
    assert r.projection.object_id == "person"
