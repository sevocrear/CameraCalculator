"""Pydantic models for camera geometry calculations."""

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, Field, model_validator


class LensType(StrEnum):
    """Optical projection model."""

    RECTILINEAR = "rectilinear"
    FISHEYE_EQUIDISTANT = "fisheye_equidistant"


class CameraParams(BaseModel):
    """Camera and mount parameters."""

    _MAX_FRAME_PIXELS: ClassVar[int] = 33_177_600  # 8K UHD: 7680 × 4320

    sensor_format_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optical format preset id (e.g. 1_2_8_inch); resolves WxH in mm",
    )
    sensor_width_mm: float | None = Field(
        default=None, gt=0, description="Sensor width in mm (optional if format_id set)"
    )
    sensor_height_mm: float | None = Field(
        default=None, gt=0, description="Sensor height in mm (optional if format_id set)"
    )
    resolution_w: int = Field(gt=0, le=8192, description="Horizontal resolution in px")
    resolution_h: int = Field(gt=0, le=8192, description="Vertical resolution in px")
    focal_length_mm: float = Field(
        gt=0,
        description=(
            "Focal length in mm; for calibrated fisheye requests, "
            "fisheye_fov_deg determines the effective focal length"
        ),
    )
    lens_type: LensType = LensType.RECTILINEAR
    fisheye_fov_deg: float | None = Field(
        default=None,
        gt=0,
        lt=360,
        description="Nominal fisheye FOV in degrees (calibrates effective f)",
    )
    distance_m: float = Field(default=1.0, ge=0.01, le=100.0)
    mount_height_m: float = Field(default=2.5, ge=0.0, le=20.0)

    @model_validator(mode="after")
    def resolve_sensor_dimensions(self) -> "CameraParams":
        """Resolve sensor WxH from optical format preset or require explicit mm."""
        if self.sensor_format_id:
            from cctv_lens_calc.domain.presets import get_sensor

            sensor = get_sensor(self.sensor_format_id)
            if sensor is None:
                raise ValueError(f"Unknown sensor_format_id: {self.sensor_format_id}")
            object.__setattr__(self, "sensor_width_mm", sensor.width_mm)
            object.__setattr__(self, "sensor_height_mm", sensor.height_mm)
        elif self.sensor_width_mm is None or self.sensor_height_mm is None:
            raise ValueError(
                "Either sensor_format_id or both sensor_width_mm and sensor_height_mm are required"
            )
        if self.resolution_w * self.resolution_h > self._MAX_FRAME_PIXELS:
            raise ValueError(f"Frame may not exceed {self._MAX_FRAME_PIXELS} pixels (8K UHD)")
        return self


class ObjectParams(BaseModel):
    """Reference or custom object for pixel projection."""

    object_id: str = Field(default="cola_can", max_length=64)
    object_width_m: float | None = Field(default=None, gt=0)
    object_height_m: float | None = Field(default=None, gt=0)
    object_distance_m: float | None = Field(default=None, ge=0.01, le=100.0)
    # Offsets of the object center relative to the camera coordinate frame.
    object_offset_y_m: float = Field(default=0.0, ge=-10.0, le=10.0)
    object_offset_x_m: float = Field(
        default=0.0,
        ge=-10.0,
        le=10.0,
        description="Lateral offset: positive values move the object right",
    )


class CalculateRequest(BaseModel):
    """Full calculation request."""

    camera: CameraParams
    object: ObjectParams = Field(default_factory=ObjectParams)


class FovMetrics(BaseModel):
    """Field of view angles in degrees."""

    hfov_deg: float
    vfov_deg: float
    dfov_deg: float


class CoverageMetrics(BaseModel):
    """Scene footprint at target distance."""

    width_m: float | None
    height_m: float | None
    distance_m: float


class DensityMetrics(BaseModel):
    """Pixel density at target distance."""

    ppm: float | None
    ppc: float | None
    gsd_mm_per_px: float | None
    basis: str


class PixelProjection(BaseModel):
    """Object size in image pixels (thin-lens / equidistant on optical axis)."""

    object_id: str
    label: str
    width_px: float
    height_px: float
    center_u_px: float
    center_v_px: float
    object_distance_m: float
    object_width_m: float
    object_height_m: float
    object_depth_m: float
    # Model alignment in the camera coordinate frame.
    object_offset_y_m: float
    object_offset_x_m: float
    orientation: str
    aspect_wh: float
    cv_pass: bool
    cv_threshold_px: float


class DoriDistances(BaseModel):
    """EN 62676-4 distance thresholds in meters."""

    detection_m: float | None
    observation_m: float | None
    recognition_m: float | None
    identification_m: float | None
    basis: str


class CalculateResponse(BaseModel):
    """Complete calculation result."""

    fov: FovMetrics
    coverage: CoverageMetrics
    density: DensityMetrics
    dori: DoriDistances
    projection: PixelProjection | None = None
    warnings: list[str] = Field(default_factory=list)
