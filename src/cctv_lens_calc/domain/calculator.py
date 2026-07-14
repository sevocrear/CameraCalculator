"""Main calculation orchestrator."""

import math

from cctv_lens_calc.domain import dori, fisheye, pinhole
from cctv_lens_calc.domain import projection as proj_math
from cctv_lens_calc.domain.models import (
    CalculateRequest,
    CalculateResponse,
    CoverageMetrics,
    DensityMetrics,
    DoriDistances,
    FovMetrics,
    LensType,
    PixelProjection,
)
from cctv_lens_calc.domain.presets import CV_THRESHOLDS
from cctv_lens_calc.domain.reference_objects import ObjectOrientation, get_object


def _resolve_focal(camera) -> float:
    """Return effective focal length, calibrating fisheye from nominal FOV."""
    if camera.lens_type == LensType.FISHEYE_EQUIDISTANT and camera.fisheye_fov_deg is not None:
        return fisheye.effective_focal_from_fov(camera.sensor_width_mm, camera.fisheye_fov_deg)
    return camera.focal_length_mm


def _geometry_module(lens_type: LensType):
    if lens_type == LensType.FISHEYE_EQUIDISTANT:
        return fisheye
    return pinhole


def _round_optional(value: float | None, digits: int) -> float | None:
    """Round a numeric metric while preserving an unavailable value."""
    return round(value, digits) if value is not None else None


def calculate(request: CalculateRequest) -> CalculateResponse:
    """Run full camera geometry calculation.

    Args:
        request: Camera and optional object parameters.

    Returns:
        FOV, coverage, density, DORI distances, and object projection.
    """
    cam = request.camera
    geom = _geometry_module(cam.lens_type)
    f_mm = _resolve_focal(cam)

    sensor_diag = math.sqrt(cam.sensor_width_mm**2 + cam.sensor_height_mm**2)

    hfov = geom.fov_deg(cam.sensor_width_mm, f_mm)
    vfov = geom.fov_deg(cam.sensor_height_mm, f_mm)
    dfov = geom.fov_deg(sensor_diag, f_mm)

    cov_w = geom.coverage_m(hfov, cam.distance_m)
    cov_h = geom.coverage_m(vfov, cam.distance_m)

    warnings: list[str] = []
    if cov_w is None:
        ppm = ppc = gsd = None
        dori_raw = {
            "detection_m": None,
            "observation_m": None,
            "recognition_m": None,
            "identification_m": None,
        }
        density_basis = "unavailable_unbounded_forward_plane"
        dori_basis = "unavailable_unbounded_forward_plane"
        warnings.append(
            "The selected horizontal FOV has no bounded footprint on a forward "
            "plane; coverage width, density, and DORI are unavailable."
        )
    else:
        ppm = cam.resolution_w / cov_w
        ppc = ppm / 100.0
        gsd = 1000.0 / ppm
        coverage_per_m = geom.coverage_m(hfov, 1.0)
        if coverage_per_m is None:  # guarded by cov_w, retained for type safety
            raise ValueError("Coverage slope is unavailable")
        dori_raw = dori.dori_distances_from_coverage(cam.resolution_w, coverage_per_m)
        if cam.lens_type == LensType.FISHEYE_EQUIDISTANT:
            density_basis = "frame_average_forward_plane"
            dori_basis = "approximate_frame_average_en_62676_4"
            warnings.append(
                "Fisheye pixel density varies across the frame; reported density "
                "and DORI use a frame-average forward-plane convention."
            )
        else:
            density_basis = "forward_plane_horizontal"
            dori_basis = "horizontal_en_62676_4"

    projection = None
    obj_req = request.object
    ref = get_object(obj_req.object_id)

    obj_w = obj_req.object_width_m
    obj_h = obj_req.object_height_m
    base_obj_z = obj_req.object_distance_m or cam.distance_m
    req_off_y = obj_req.object_offset_y_m or 0.0
    req_off_x = obj_req.object_offset_x_m or 0.0

    obj_d = 0.0
    label = obj_req.object_id
    cv_threshold = CV_THRESHOLDS["embedder_min_px"]
    orientation = ObjectOrientation.UPRIGHT.value
    total_off_y = req_off_y
    total_off_x = req_off_x
    scale_mul = 1.0

    if ref is not None:
        total_off_y = req_off_y + ref.model_offset_y_m
        total_off_x = req_off_x + ref.model_offset_x_m
        scale_mul = ref.model_scale_mul

        obj_w = obj_w or ref.width_m * scale_mul
        obj_h = obj_h or ref.height_m * scale_mul
        obj_d = ref.depth_m * scale_mul
        label = ref.label
        cv_threshold = ref.cv_threshold_px
        orientation = ref.orientation.value
    elif obj_w is None or obj_h is None:
        obj_w = obj_w or 0.1
        obj_h = obj_h or 0.1

    obj_z = max(base_obj_z, 0.01)

    if obj_w and obj_h:
        left, top, right, bottom = proj_math.project_box_bbox_px(
            total_off_x,
            total_off_y,
            obj_z,
            obj_w,
            obj_h,
            obj_d or 0.0,
            sensor_width_mm=cam.sensor_width_mm,
            sensor_height_mm=cam.sensor_height_mm,
            focal_length_mm=f_mm,
            resolution_w=cam.resolution_w,
            resolution_h=cam.resolution_h,
            lens_type=cam.lens_type,
        )
        px_w = right - left
        px_h = bottom - top
        min_side = min(px_w, px_h)
        aspect = px_w / px_h if px_h > 0 else 0.0
        center_u = (left + right) / 2.0
        center_v = (top + bottom) / 2.0
        projection = PixelProjection(
            object_id=obj_req.object_id,
            label=label,
            width_px=round(px_w, 1),
            height_px=round(px_h, 1),
            center_u_px=round(center_u, 3),
            center_v_px=round(center_v, 3),
            object_distance_m=obj_z,
            object_width_m=obj_w,
            object_height_m=obj_h,
            object_depth_m=float(obj_d or 0.0),
            object_offset_y_m=float(total_off_y),
            object_offset_x_m=float(total_off_x),
            orientation=orientation,
            aspect_wh=round(aspect, 4),
            cv_pass=min_side >= cv_threshold,
            cv_threshold_px=cv_threshold,
        )

    return CalculateResponse(
        fov=FovMetrics(
            hfov_deg=round(hfov, 2),
            vfov_deg=round(vfov, 2),
            dfov_deg=round(dfov, 2),
        ),
        coverage=CoverageMetrics(
            width_m=_round_optional(cov_w, 4),
            height_m=_round_optional(cov_h, 4),
            distance_m=cam.distance_m,
        ),
        density=DensityMetrics(
            ppm=_round_optional(ppm, 2),
            ppc=_round_optional(ppc, 3),
            gsd_mm_per_px=_round_optional(gsd, 4),
            basis=density_basis,
        ),
        dori=DoriDistances(
            detection_m=_round_optional(dori_raw["detection_m"], 2),
            observation_m=_round_optional(dori_raw["observation_m"], 2),
            recognition_m=_round_optional(dori_raw["recognition_m"], 2),
            identification_m=_round_optional(dori_raw["identification_m"], 2),
            basis=dori_basis,
        ),
        projection=projection,
        warnings=warnings,
    )
