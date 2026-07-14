"""Sensor and camera presets for TechVill project."""

from dataclasses import dataclass

from cctv_lens_calc.domain.models import LensType


@dataclass(frozen=True)
class SensorPreset:
    """Standard sensor optical format (Type) with active area in mm."""

    id: str
    label: str
    width_mm: float
    height_mm: float
    diagonal_mm: float
    aspect: str  # "4:3" | "16:9"


@dataclass(frozen=True)
class CameraPreset:
    """Pre-configured camera profile."""

    id: str
    label: str
    sensor_id: str
    resolution_w: int
    resolution_h: int
    focal_length_mm: float
    lens_type: LensType
    fisheye_fov_deg: float | None
    datasheet_url: str | None = None


SENSOR_PRESETS: dict[str, SensorPreset] = {
    "1_4_inch": SensorPreset(
        "1_4_inch", '1/4" (3.60×2.70 mm)', 3.60, 2.70, 4.5, "4:3"
    ),
    "1_3_6_inch": SensorPreset(
        "1_3_6_inch", '1/3.6" (4.00×3.00 mm)', 4.00, 3.00, 5.0, "4:3"
    ),
    "1_3_2_inch": SensorPreset(
        "1_3_2_inch", '1/3.2" (4.54×3.42 mm)', 4.54, 3.42, 5.68, "4:3"
    ),
    "1_3_inch": SensorPreset(
        "1_3_inch", '1/3" (4.80×3.60 mm)', 4.80, 3.60, 6.0, "4:3"
    ),
    "1_2_9_inch": SensorPreset(
        "1_2_9_inch", '1/2.9" (4.98×3.74 mm)', 4.98, 3.74, 6.23, "4:3"
    ),
    "1_2_8_inch": SensorPreset(
        "1_2_8_inch", '1/2.8" 16:9 (5.37×3.02 mm)', 5.37, 3.02, 6.46, "16:9"
    ),
    "1_2_8_inch_43": SensorPreset(
        "1_2_8_inch_43", '1/2.8" 4:3 (5.25×3.94 mm)', 5.25, 3.94, 6.46, "4:3"
    ),
    "1_2_7_inch": SensorPreset(
        "1_2_7_inch", '1/2.7" 16:9 (5.27×2.96 mm)', 5.27, 2.96, 6.72, "16:9"
    ),
    "1_2_5_inch": SensorPreset(
        "1_2_5_inch", '1/2.5" (5.76×4.29 mm)', 5.76, 4.29, 7.18, "4:3"
    ),
    "1_2_3_inch": SensorPreset(
        "1_2_3_inch", '1/2.3" (6.17×4.55 mm)', 6.17, 4.55, 7.66, "4:3"
    ),
    "1_2_inch": SensorPreset(
        "1_2_inch", '1/2" (6.40×4.80 mm)', 6.40, 4.80, 8.0, "4:3"
    ),
    "1_1_8_inch": SensorPreset(
        "1_1_8_inch", '1/1.8" 16:9 (7.18×4.04 mm)', 7.18, 4.04, 8.93, "16:9"
    ),
    "1_1_8_inch_43": SensorPreset(
        "1_1_8_inch_43", '1/1.8" 4:3 (7.18×5.32 mm)', 7.18, 5.32, 8.93, "4:3"
    ),
    "1_1_7_inch": SensorPreset(
        "1_1_7_inch", '1/1.7" (7.60×5.70 mm)', 7.60, 5.70, 9.5, "4:3"
    ),
    "2_3_inch": SensorPreset(
        "2_3_inch", '2/3" (8.80×6.60 mm)', 8.80, 6.60, 11.0, "4:3"
    ),
    "1_1_2_inch_169": SensorPreset(
        "1_1_2_inch_169", '1/1.2" 16:9 (11.21×6.30 mm)', 11.21, 6.30, 12.86, "16:9"
    ),
    "1_inch": SensorPreset(
        "1_inch", '1" (12.80×9.60 mm)', 12.80, 9.60, 16.0, "4:3"
    ),
    "1_1_inch": SensorPreset(
        "1_1_inch", '1.1" (14.10×10.30 mm)', 14.10, 10.30, 17.5, "4:3"
    ),
}


CAMERA_PRESETS: dict[str, CameraPreset] = {
    "optimus_p042": CameraPreset(
        id="optimus_p042",
        label="Optimus P042 (стеллажная)",
        sensor_id="1_2_8_inch",
        resolution_w=1920,
        resolution_h=1080,
        focal_length_mm=2.8,
        lens_type=LensType.RECTILINEAR,
        fisheye_fov_deg=None,
        datasheet_url="https://optimus-cctv.ru/catalog/ip-videokamery-prof-serii/videokamera-optimus-smart-ip-p042-1-2-8-mdhl/",
    ),
    "optimus_p012": CameraPreset(
        id="optimus_p012",
        label="Optimus P012 (кассовая)",
        sensor_id="1_2_8_inch",
        resolution_w=1920,
        resolution_h=1080,
        focal_length_mm=2.8,
        lens_type=LensType.RECTILINEAR,
        fisheye_fov_deg=None,
        datasheet_url="https://optimus-cctv.ru/catalog/ip-videokamery-prof-serii/videokamera-optimus-smart-ip-p012-1-4x-d/",
    ),
    "shelf_usb_fisheye": CameraPreset(
        id="shelf_usb_fisheye",
        label="USB внутриполочная (~160° fisheye)",
        sensor_id="1_2_7_inch",
        resolution_w=1920,
        resolution_h=1080,
        focal_length_mm=1.5,
        lens_type=LensType.FISHEYE_EQUIDISTANT,
        fisheye_fov_deg=160.0,
        datasheet_url=None,
    ),
    "ceiling_fisheye_1080p": CameraPreset(
        id="ceiling_fisheye_1080p",
        label="Потолочная fisheye 1080p",
        sensor_id="1_1_8_inch",
        resolution_w=1920,
        resolution_h=1080,
        focal_length_mm=1.4,
        lens_type=LensType.FISHEYE_EQUIDISTANT,
        fisheye_fov_deg=180.0,
        datasheet_url=None,
    ),
}


CV_THRESHOLDS = {
    "detector_min_px": 32.0,
    "embedder_min_px": 64.0,
    "sku_confident_px": 100.0,
}


def get_sensor(sensor_id: str) -> SensorPreset | None:
    return SENSOR_PRESETS.get(sensor_id)


def get_camera(camera_id: str) -> CameraPreset | None:
    return CAMERA_PRESETS.get(camera_id)


def camera_to_params(camera_id: str) -> dict | None:
    """Expand camera preset to flat parameter dict."""
    cam = get_camera(camera_id)
    if cam is None:
        return None
    sensor = get_sensor(cam.sensor_id)
    if sensor is None:
        return None
    focal = cam.focal_length_mm
    if cam.lens_type == LensType.FISHEYE_EQUIDISTANT and cam.fisheye_fov_deg:
        from cctv_lens_calc.domain.fisheye import effective_focal_from_fov

        focal = effective_focal_from_fov(sensor.width_mm, cam.fisheye_fov_deg)
    return {
        "sensor_format_id": cam.sensor_id,
        "sensor_width_mm": sensor.width_mm,
        "sensor_height_mm": sensor.height_mm,
        "resolution_w": cam.resolution_w,
        "resolution_h": cam.resolution_h,
        "focal_length_mm": focal,
        "lens_type": cam.lens_type.value,
        "fisheye_fov_deg": cam.fisheye_fov_deg,
        "preset_id": cam.id,
        "preset_label": cam.label,
    }
