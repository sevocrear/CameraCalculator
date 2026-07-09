"""Fisheye equidistant geometry tests."""

import pytest

from cctv_lens_calc.domain import fisheye, pinhole


def test_fisheye_160_hfov():
    sensor_w = 5.27
    f = fisheye.effective_focal_from_fov(sensor_w, 160.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    assert hfov == pytest.approx(160.0, abs=1.0)


def test_fisheye_180_hfov():
    sensor_w = 7.18
    f = fisheye.effective_focal_from_fov(sensor_w, 180.0)
    hfov = fisheye.fov_deg(sensor_w, f)
    assert hfov == pytest.approx(180.0, abs=1.0)


def test_pinhole_fisheye_small_angle_convergence():
    """Small object on axis: fisheye ≈ pinhole within 2%."""
    obj_w, obj_h, z = 0.066, 0.12, 0.45
    sw, sh, f, rw, rh = 5.37, 3.02, 2.8, 1920, 1080
    px_pin = pinhole.object_pixels(obj_w, obj_h, z, sw, sh, f, rw, rh)
    px_fish = fisheye.object_pixels(obj_w, obj_h, z, sw, sh, f, rw, rh)
    for a, b in zip(px_pin, px_fish):
        assert abs(a - b) / a < 0.02
