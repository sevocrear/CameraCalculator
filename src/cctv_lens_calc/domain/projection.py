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
        radial_distance_m = math.hypot(obj_x_m, obj_y_m)
        if radial_distance_m <= 1e-12:
            return cx, cy
        theta_rad = math.atan2(radial_distance_m, z)
        radius_mm = focal_length_mm * theta_rad
        sensor_x_mm = radius_mm * obj_x_m / radial_distance_m
        sensor_y_mm = radius_mm * obj_y_m / radial_distance_m
        u = cx + sensor_x_mm / pitch_w
        v = cy - sensor_y_mm / pitch_h
        return u, v

    fx = (focal_length_mm / sensor_width_mm) * resolution_w
    fy = (focal_length_mm / sensor_height_mm) * resolution_h
    u = cx + (fx * obj_x_m) / z
    v = cy - (fy * obj_y_m) / z
    return u, v


def project_box_bbox_px(
    center_x_m: float,
    center_y_m: float,
    distance_m: float,
    width_m: float,
    height_m: float,
    depth_m: float,
    *,
    sensor_width_mm: float,
    sensor_height_mm: float,
    focal_length_mm: float,
    resolution_w: int,
    resolution_h: int,
    lens_type: LensType,
) -> tuple[float, float, float, float]:
    """Project a camera-aligned physical box and return its pixel AABB.

    Both depth faces are included. Equidistant projection is radial, so extrema
    can occur where a box edge passes closest to the optical axis rather than at
    a corner. The candidate grid includes both bounds and the nearest-to-zero
    point on each image-plane axis.
    """
    half_width = width_m / 2.0
    half_height = height_m / 2.0
    x_min, x_max = center_x_m - half_width, center_x_m + half_width
    y_min, y_max = center_y_m - half_height, center_y_m + half_height
    nearest_x = min(max(0.0, x_min), x_max)
    nearest_y = min(max(0.0, y_min), y_max)
    half_depth = depth_m / 2.0
    z_near = max(distance_m - half_depth, 1e-6)
    z_far = distance_m + half_depth
    candidates = tuple(
        (x_m, y_m, z_m)
        for x_m in (x_min, nearest_x, x_max)
        for y_m in (y_min, nearest_y, y_max)
        for z_m in (z_near, z_far)
    )
    projected = [
        project_point_px(
            x_m,
            y_m,
            z_m,
            sensor_width_mm=sensor_width_mm,
            sensor_height_mm=sensor_height_mm,
            focal_length_mm=focal_length_mm,
            resolution_w=resolution_w,
            resolution_h=resolution_h,
            lens_type=lens_type,
        )
        for x_m, y_m, z_m in candidates
    ]
    u_values = [point[0] for point in projected]
    v_values = [point[1] for point in projected]
    return min(u_values), min(v_values), max(u_values), max(v_values)
