"""Main calculation orchestrator."""

import math

from cctv_lens_calc.domain import dori, fisheye, pinhole
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
    if (
        camera.lens_type == LensType.FISHEYE_EQUIDISTANT
        and camera.fisheye_fov_deg is not None
    ):
        return fisheye.effective_focal_from_fov(
            camera.sensor_width_mm, camera.fisheye_fov_deg
        )
    return camera.focal_length_mm


def _geometry_module(lens_type: LensType):
    if lens_type == LensType.FISHEYE_EQUIDISTANT:
        return fisheye
    return pinhole


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
    cov_h = pinhole.coverage_m(vfov, cam.distance_m)

    ppm = cam.resolution_w / cov_w
    ppc = ppm / 100.0
    gsd = pinhole.gsd_mm_per_px(
        cam.distance_m,
        cam.sensor_width_mm,
        f_mm,
        cam.resolution_w,
    )

    dori_raw = dori.dori_distances(
        cam.resolution_w, cam.sensor_width_mm, f_mm
    )

    projection = None
    obj_req = request.object
    ref = get_object(obj_req.object_id)

    obj_w = obj_req.object_width_m
    obj_h = obj_req.object_height_m
    base_obj_z = obj_req.object_distance_m or cam.distance_m
    # Semantics:
    # - object_offset_y_m — вертикальный сдвиг центра объекта
    # - object_offset_z_m — ЛЕВО/ПРАВО (сдвиг по X) в камере/на изображении.
    #   Это соответствует твоему замечанию: "model_offset_z_m должен быть x".
    req_off_y = obj_req.object_offset_y_m or 0.0
    req_off_z = obj_req.object_offset_z_m or 0.0

    obj_d = 0.0
    label = obj_req.object_id
    cv_threshold = CV_THRESHOLDS["embedder_min_px"]
    orientation = ObjectOrientation.UPRIGHT.value
    total_off_y = req_off_y
    total_off_z = req_off_z
    scale_mul = 1.0

    if ref is not None:
        total_off_y = req_off_y + ref.model_offset_y_m
        total_off_z = req_off_z + ref.model_offset_z_m  # actually -> offset_x_m
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

    obj_z = base_obj_z
    obj_z = max(obj_z, 0.01)  # keep camera model stable
    obj_y_off = total_off_y
    obj_x_off = total_off_z

    if obj_w and obj_h:
        px_w, px_h = geom.object_pixels(
            obj_w,
            obj_h,
            obj_z,
            cam.sensor_width_mm,
            cam.sensor_height_mm,
            f_mm,
            cam.resolution_w,
            cam.resolution_h,
        )
        min_side = min(px_w, px_h)
        aspect = px_w / px_h if px_h > 0 else 0.0
        # Camera intrinsics for projecting object center (X=0, Y=obj_y_off).
        fx = (f_mm / cam.sensor_width_mm) * cam.resolution_w
        fy = (f_mm / cam.sensor_height_mm) * cam.resolution_h
        center_u = cam.resolution_w / 2.0 + (fx * obj_x_off) / obj_z
        center_v = cam.resolution_h / 2.0 - (fy * obj_y_off) / obj_z
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
            # В ответе field оставляем как object_offset_z_m, но семантика = сдвиг по X.
            object_offset_z_m=float(obj_x_off),
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
            width_m=round(cov_w, 4),
            height_m=round(cov_h, 4),
            distance_m=cam.distance_m,
        ),
        density=DensityMetrics(
            ppm=round(ppm, 2),
            ppc=round(ppc, 3),
            gsd_mm_per_px=round(gsd, 4),
        ),
        dori=DoriDistances(
            detection_m=round(dori_raw["detection_m"], 2),
            observation_m=round(dori_raw["observation_m"], 2),
            recognition_m=round(dori_raw["recognition_m"], 2),
            identification_m=round(dori_raw["identification_m"], 2),
        ),
        projection=projection,
    )
