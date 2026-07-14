"""Rectilinear (pinhole) camera geometry."""

import math

# tan(90°) ломает coverage/frustum — для визуализации и PPM cap на 89.95°.
_MAX_HALF_FOV_DEG = 89.95


def safe_tan_half_fov(fov_deg_val: float) -> float:
    """tan(FOV/2) with cap so wide-angle math stays finite."""
    half_deg = min(fov_deg_val / 2.0, _MAX_HALF_FOV_DEG)
    return math.tan(math.radians(half_deg))


def fov_deg(sensor_dim_mm: float, focal_length_mm: float) -> float:
    """Field of view angle in degrees for one sensor dimension.

    Args:
        sensor_dim_mm: Sensor width, height, or diagonal in mm.
        focal_length_mm: Focal length in mm.

    Returns:
        FOV in degrees: 2 * atan(d / 2f).
    """
    return math.degrees(2.0 * math.atan(sensor_dim_mm / (2.0 * focal_length_mm)))


def coverage_m(fov_deg_val: float, distance_m: float) -> float:
    """Scene width or height at perpendicular distance Z.

    Args:
        fov_deg_val: Horizontal or vertical FOV in degrees.
        distance_m: Distance to scene plane in meters.

    Returns:
        Coverage dimension in meters: 2 * Z * tan(FOV/2).
    """
    return 2.0 * distance_m * safe_tan_half_fov(fov_deg_val)


def ppm_at_distance(
    resolution_w: int,
    sensor_width_mm: float,
    focal_length_mm: float,
    distance_m: float,
) -> float:
    """Pixels per meter at distance Z (horizontal).

    PPM = resolution_w / coverage_width_m.
    """
    hfov = fov_deg(sensor_width_mm, focal_length_mm)
    width_m = coverage_m(hfov, distance_m)
    return resolution_w / width_m


def gsd_mm_per_px(
    distance_m: float,
    sensor_width_mm: float,
    focal_length_mm: float,
    resolution_w: int,
) -> float:
    """Ground sample distance in mm per pixel at distance Z."""
    return (distance_m * sensor_width_mm * 1000.0) / (focal_length_mm * resolution_w)


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
    """Project object size to image pixels (thin-lens, on optical axis).

    px_w = object_w * resolution_w * f / (Z * sensor_w)

    Returns:
        (width_px, height_px)
    """
    px_w = (
        object_width_m * resolution_w * focal_length_mm
        / (object_distance_m * sensor_width_mm)
    )
    px_h = (
        object_height_m * resolution_h * focal_length_mm
        / (object_distance_m * sensor_height_mm)
    )
    return px_w, px_h
