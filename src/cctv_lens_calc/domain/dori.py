"""EN 62676-4 DORI pixel density thresholds."""

# Pixels per meter thresholds (horizontal)
DORI_DETECTION_PPM = 25.0
DORI_OBSERVATION_PPM = 62.5
DORI_RECOGNITION_PPM = 125.0
DORI_IDENTIFICATION_PPM = 250.0


def distance_for_ppm(
    required_ppm: float,
    resolution_w: int,
    sensor_width_mm: float,
    focal_length_mm: float,
) -> float:
    """Distance at which horizontal PPM equals required threshold.

    From PPM = res_w / W and W = 2*Z*tan(HFOV/2), HFOV = 2*atan(sensor_w/2f):
    W = Z * sensor_w / f  (small-angle / JVSG simplified formula)
    PPM = res_w * f / (Z * sensor_w)
    Z = res_w * f / (PPM * sensor_w)

    Args:
        required_ppm: Target pixels per meter.
        resolution_w: Horizontal resolution.
        sensor_width_mm: Sensor width in mm.
        focal_length_mm: Focal length in mm.

    Returns:
        Distance in meters.
    """
    return (resolution_w * focal_length_mm) / (required_ppm * sensor_width_mm)


def dori_distances(
    resolution_w: int,
    sensor_width_mm: float,
    focal_length_mm: float,
) -> dict[str, float]:
    """Compute DORI zone distances in meters."""
    return {
        "detection_m": distance_for_ppm(
            DORI_DETECTION_PPM, resolution_w, sensor_width_mm, focal_length_mm
        ),
        "observation_m": distance_for_ppm(
            DORI_OBSERVATION_PPM, resolution_w, sensor_width_mm, focal_length_mm
        ),
        "recognition_m": distance_for_ppm(
            DORI_RECOGNITION_PPM, resolution_w, sensor_width_mm, focal_length_mm
        ),
        "identification_m": distance_for_ppm(
            DORI_IDENTIFICATION_PPM, resolution_w, sensor_width_mm, focal_length_mm
        ),
    }
