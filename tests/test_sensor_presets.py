"""Sensor format presets: table integrity and JVSG reference dimensions."""

import math

import pytest

from cctv_lens_calc.domain import pinhole
from cctv_lens_calc.domain.models import CameraParams, LensType
from cctv_lens_calc.domain.presets import CAMERA_PRESETS, SENSOR_PRESETS, get_sensor


def test_sensor_presets_count():
    assert len(SENSOR_PRESETS) >= 15


@pytest.mark.parametrize("sensor_id,preset", SENSOR_PRESETS.items())
def test_sensor_preset_positive_dims(sensor_id, preset):
    assert preset.width_mm > 0
    assert preset.height_mm > 0
    assert preset.diagonal_mm > 0
    assert preset.aspect in ("4:3", "16:9")
    assert '"' in preset.label or "inch" in preset.label.lower()


def test_jvsg_reference_formats():
    s13 = get_sensor("1_3_inch")
    s12 = get_sensor("1_2_inch")
    assert s13 is not None
    assert s12 is not None
    assert s13.width_mm == pytest.approx(4.8, abs=0.01)
    assert s13.height_mm == pytest.approx(3.6, abs=0.01)
    assert s12.width_mm == pytest.approx(6.4, abs=0.01)
    assert s12.height_mm == pytest.approx(4.8, abs=0.01)


def test_camera_presets_reference_valid_sensor():
    for cam_id, cam in CAMERA_PRESETS.items():
        sensor = get_sensor(cam.sensor_id)
        assert sensor is not None, f"{cam_id} -> missing {cam.sensor_id}"


def test_hikvision_preset_uses_official_datasheet():
    preset = CAMERA_PRESETS["hikvision_ds_2cd2183g2_is"]
    assert preset.datasheet_url is not None
    assert preset.datasheet_url.startswith("https://www.hikvision.com/")


def test_sensor_format_id_resolves_mm():
    cam = CameraParams(
        sensor_format_id="1_3_inch",
        resolution_w=1920,
        resolution_h=1080,
        focal_length_mm=4.0,
    )
    assert cam.sensor_width_mm == pytest.approx(4.8)
    assert cam.sensor_height_mm == pytest.approx(3.6)


def test_sensor_format_id_overrides_explicit_mm():
    """Format id is authoritative when both are sent (UI path)."""
    cam = CameraParams(
        sensor_format_id="1_3_inch",
        sensor_width_mm=99.0,
        sensor_height_mm=99.0,
        resolution_w=1920,
        resolution_h=1080,
        focal_length_mm=4.0,
    )
    assert cam.sensor_width_mm == pytest.approx(4.8)
    assert cam.sensor_height_mm == pytest.approx(3.6)


def test_unknown_sensor_format_raises():
    with pytest.raises(ValueError, match="Unknown sensor_format_id"):
        CameraParams(
            sensor_format_id="9_9_inch",
            resolution_w=1920,
            resolution_h=1080,
            focal_length_mm=4.0,
        )


def test_frame_resolution_is_bounded():
    with pytest.raises(ValueError, match="8K UHD"):
        CameraParams(
            sensor_format_id="1_2_8_inch",
            resolution_w=8192,
            resolution_h=8192,
            focal_length_mm=2.8,
        )


def test_larger_format_wider_hfov_at_same_focal():
    f_mm = 2.8
    small = get_sensor("1_3_inch")
    large = get_sensor("1_2_inch")
    hfov_small = pinhole.fov_deg(small.width_mm, f_mm)
    hfov_large = pinhole.fov_deg(large.width_mm, f_mm)
    assert hfov_large > hfov_small


def test_fov_identity_hfov_formula():
    """HFOV = 2·atan(W/(2f)) for rectilinear preset."""
    sensor = get_sensor("1_2_8_inch")
    f_mm = 2.8
    expected = math.degrees(2 * math.atan(sensor.width_mm / (2 * f_mm)))
    cam = CameraParams(
        sensor_format_id="1_2_8_inch",
        resolution_w=1920,
        resolution_h=1080,
        focal_length_mm=f_mm,
        lens_type=LensType.RECTILINEAR,
    )
    from cctv_lens_calc.domain.calculator import calculate
    from cctv_lens_calc.domain.models import CalculateRequest, ObjectParams

    result = calculate(CalculateRequest(camera=cam, object=ObjectParams(object_id="cola_can")))
    assert result.fov.hfov_deg == pytest.approx(expected, rel=1e-4)
