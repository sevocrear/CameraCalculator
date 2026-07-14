"""Pydantic models for camera geometry calculations."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class LensType(str, Enum):
    """Optical projection model."""

    RECTILINEAR = "rectilinear"
    FISHEYE_EQUIDISTANT = "fisheye_equidistant"


class CameraParams(BaseModel):
    """Camera and mount parameters."""

    sensor_format_id: str | None = Field(
        default=None,
        description="Optical format preset id (e.g. 1_2_8_inch); resolves WxH in mm",
    )
    sensor_width_mm: float | None = Field(
        default=None, gt=0, description="Sensor width in mm (optional if format_id set)"
    )
    sensor_height_mm: float | None = Field(
        default=None, gt=0, description="Sensor height in mm (optional if format_id set)"
    )
    resolution_w: int = Field(gt=0, description="Horizontal resolution in px")
    resolution_h: int = Field(gt=0, description="Vertical resolution in px")
    focal_length_mm: float = Field(gt=0, description="Focal length in mm")
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
                "Either sensor_format_id or both sensor_width_mm and sensor_height_mm "
                "are required"
            )
        return self


class ObjectParams(BaseModel):
    """Reference or custom object for pixel projection."""

    object_id: str = "cola_can"
    object_width_m: float | None = Field(default=None, gt=0)
    object_height_m: float | None = Field(default=None, gt=0)
    object_distance_m: float | None = Field(default=None, ge=0.01, le=100.0)
    # Offsets of the object center relative to the camera coordinate frame:
    # - +Y means higher than camera mount height
    # - +Z means further away from the camera along the optical axis
    object_offset_y_m: float = Field(default=0.0, ge=-10.0, le=10.0)
    object_offset_z_m: float = Field(default=0.0, ge=-10.0, le=10.0)


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

    width_m: float
    height_m: float
    distance_m: float


class DensityMetrics(BaseModel):
    """Pixel density at target distance."""

    ppm: float
    ppc: float
    gsd_mm_per_px: float


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
    # Model alignment (presets/config):
    # how the object "center point" is shifted relative to the camera when projecting.
    object_offset_y_m: float
    object_offset_z_m: float
    orientation: str
    aspect_wh: float
    cv_pass: bool
    cv_threshold_px: float


class DoriDistances(BaseModel):
    """EN 62676-4 distance thresholds in meters."""

    detection_m: float
    observation_m: float
    recognition_m: float
    identification_m: float


class CalculateResponse(BaseModel):
    """Complete calculation result."""

    fov: FovMetrics
    coverage: CoverageMetrics
    density: DensityMetrics
    dori: DoriDistances
    projection: PixelProjection | None = None
