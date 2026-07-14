"""Equidistant fisheye projection: r = f * theta."""

import math

from cctv_lens_calc.domain import pinhole


def effective_focal_from_fov(sensor_width_mm: float, fisheye_fov_deg: float) -> float:
    """Derive effective focal length from nominal horizontal fisheye FOV.

    For equidistant fisheye: theta_max = sensor_half_width / f.
    Given nominal HFOV: f = (sensor_w/2) / theta_max_rad.

    Args:
        sensor_width_mm: Sensor width in mm.
        fisheye_fov_deg: Nominal horizontal FOV in degrees.

    Returns:
        Effective focal length in mm.
    """
    theta_max_rad = math.radians(fisheye_fov_deg / 2.0)
    return (sensor_width_mm / 2.0) / theta_max_rad


def fov_deg(sensor_dim_mm: float, focal_length_mm: float) -> float:
    """FOV for equidistant fisheye: theta_max = r_sensor / f."""
    theta_max_rad = (sensor_dim_mm / 2.0) / focal_length_mm
    return math.degrees(2.0 * theta_max_rad)


def coverage_m(hfov_deg: float, distance_m: float) -> float:
    """Scene width at distance Z for equidistant fisheye edge ray.

    Ray at image edge has angle theta_max = HFOV/2 from optical axis;
    lateral offset on plane at Z is Z * tan(theta_max). Capped for theta → 90°
    and for ultra-wide FOV in UI metrics.
    """
    theta_max_rad = math.radians(min(hfov_deg / 2.0, pinhole._MAX_HALF_FOV_DEG))
    raw = 2.0 * distance_m * math.tan(theta_max_rad)
    if hfov_deg >= 150.0:
        return min(raw, 2.0 * distance_m)
    return raw


def object_pixels(
    object_width_m: float,
    object_height_m: float,
    object_distance_m: float,
    sensor_width_mm: float,
    sensor_height_mm: float,
    focal_length_mm: float,
    resolution_w: int,
    resolution_h: int,
) -> tuple[float, float]:
    """Project object to pixels using equidistant fisheye on optical axis.

    Angular half-extents theta_w = atan(S/2Z), r = f * theta, px = r / pitch.
    """
    pixel_pitch_w_mm = sensor_width_mm / resolution_w
    pixel_pitch_h_mm = sensor_height_mm / resolution_h

    theta_w = math.atan(object_width_m / (2.0 * object_distance_m))
    theta_h = math.atan(object_height_m / (2.0 * object_distance_m))

    r_w_mm = focal_length_mm * theta_w
    r_h_mm = focal_length_mm * theta_h

    px_w = 2.0 * r_w_mm / pixel_pitch_w_mm
    px_h = 2.0 * r_h_mm / pixel_pitch_h_mm
    return px_w, px_h
