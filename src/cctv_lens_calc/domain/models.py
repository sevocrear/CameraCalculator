"""Pydantic models for camera geometry calculations."""

from enum import Enum

from pydantic import BaseModel, Field


class LensType(str, Enum):
    """Optical projection model."""

    RECTILINEAR = "rectilinear"
    FISHEYE_EQUIDISTANT = "fisheye_equidistant"


class CameraParams(BaseModel):
    """Camera and mount parameters."""

    sensor_width_mm: float = Field(gt=0, description="Sensor width in mm")
    sensor_height_mm: float = Field(gt=0, description="Sensor height in mm")
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
