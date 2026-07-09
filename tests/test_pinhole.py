"""Pinhole geometry unit tests vs JVSG reference values."""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cctv_lens_calc.domain import pinhole


def test_jvsg_coverage_1_3_inch_4mm_10m():
    """JVSG simplified: W = Z * sensor_w / f = 10 * 4.8 / 4 = 12 m."""
    hfov = pinhole.fov_deg(4.8, 4.0)
    width = pinhole.coverage_m(hfov, 10.0)
    assert width == pytest.approx(12.0, rel=0.005)


def test_hfov_1_3_inch_4mm():
    expected = math.degrees(2 * math.atan(4.8 / (2 * 4.0)))
    assert pinhole.fov_deg(4.8, 4.0) == pytest.approx(expected, rel=1e-4)
    assert pinhole.fov_deg(4.8, 4.0) == pytest.approx(61.93, abs=0.1)


def test_ppm_at_10m():
    hfov = pinhole.fov_deg(4.8, 4.0)
    width = pinhole.coverage_m(hfov, 10.0)
    ppm = 1920 / width
    assert ppm == pytest.approx(160.0, rel=0.01)


def test_gsd_positive():
    gsd = pinhole.gsd_mm_per_px(10.0, 4.8, 4.0, 1920)
    assert gsd > 0


@given(
    z=st.floats(min_value=0.5, max_value=30.0),
    f=st.floats(min_value=1.0, max_value=12.0),
)
@settings(max_examples=50)
def test_property_z_increases_ppc_decreases(z, f):
    sensor_w = 4.8
    res = 1920
    hfov = pinhole.fov_deg(sensor_w, f)
    w_near = pinhole.coverage_m(hfov, z)
    w_far = pinhole.coverage_m(hfov, z * 2)
    ppc_near = res / w_near / 100
    ppc_far = res / w_far / 100
    assert ppc_near > ppc_far


@given(f=st.floats(min_value=1.0, max_value=12.0))
@settings(max_examples=30)
def test_property_f_increases_hfov_decreases(f):
    hfov = pinhole.fov_deg(4.8, f)
    hfov_wide = pinhole.fov_deg(4.8, f * 0.5)
    assert hfov < hfov_wide
