"""Unified 3D→2D projection for rectilinear and equidistant fisheye cameras.

Camera frame (ceiling mount, optical axis along −Z in world):
  - X: right, Y: up, Z: forward (distance into scene)
  - Image u grows right, v grows down
"""

import math

from cctv_lens_calc.domain.models import LensType


def pixel_pitch_mm(sensor_mm: float, resolution_px: int) -> float:
    """Sensor mm per image pixel along one axis."""
    return sensor_mm / resolution_px


def rectilinear_focal_from_hfov(sensor_width_mm: float, hfov_deg: float) -> float:
    """Focal length (mm) for target horizontal FOV (pinhole)."""
    half_rad = math.radians(hfov_deg / 2.0)
    return (sensor_width_mm / 2.0) / math.tan(half_rad)


def project_point_px(
    obj_x_m: float,
    obj_y_m: float,
    obj_z_m: float,
    *,
    sensor_width_mm: float,
    sensor_height_mm: float,
    focal_length_mm: float,
    resolution_w: int,
    resolution_h: int,
    lens_type: LensType,
) -> tuple[float, float]:
    """Project object center (camera frame) to image pixel coordinates (u, v).

    Args:
        obj_x_m: Lateral offset (+ right).
        obj_y_m: Vertical offset (+ above camera height).
        obj_z_m: Distance along optical axis (must be > 0).
        sensor_width_mm: Sensor width.
        sensor_height_mm: Sensor height.
        focal_length_mm: Effective focal length in mm.
        resolution_w: Image width in px.
        resolution_h: Image height in px.
        lens_type: Optical model.

    Returns:
        (center_u_px, center_v_px) with origin top-left, v down.
    """
    z = max(obj_z_m, 1e-6)
    cx = resolution_w / 2.0
    cy = resolution_h / 2.0

    if lens_type == LensType.FISHEYE_EQUIDISTANT:
        pitch_w = pixel_pitch_mm(sensor_width_mm, resolution_w)
        pitch_h = pixel_pitch_mm(sensor_height_mm, resolution_h)
        theta_x = math.atan2(obj_x_m, z)
        theta_y = math.atan2(obj_y_m, z)
        r_x_mm = focal_length_mm * theta_x
        r_y_mm = focal_length_mm * theta_y
        u = cx + r_x_mm / pitch_w
        v = cy - r_y_mm / pitch_h
        return u, v

    fx = (focal_length_mm / sensor_width_mm) * resolution_w
    fy = (focal_length_mm / sensor_height_mm) * resolution_h
    u = cx + (fx * obj_x_m) / z
    v = cy - (fy * obj_y_m) / z
    return u, v


def bbox_from_center_size(
    center_u: float,
    center_v: float,
    width_px: float,
    height_px: float,
) -> tuple[float, float, float, float]:
    """Axis-aligned bbox (left, top, right, bottom) in pixels."""
    half_w = width_px / 2.0
    half_h = height_px / 2.0
    return (
        center_u - half_w,
        center_v - half_h,
        center_u + half_w,
        center_v + half_h,
    )
