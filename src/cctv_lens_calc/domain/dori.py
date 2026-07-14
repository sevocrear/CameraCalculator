"""EN 62676-4 DORI pixel density thresholds."""

# Pixels per meter thresholds (horizontal)
DORI_DETECTION_PPM = 25.0
DORI_OBSERVATION_PPM = 62.5
DORI_RECOGNITION_PPM = 125.0
DORI_IDENTIFICATION_PPM = 250.0


def distance_for_coverage_ppm(
    required_ppm: float,
    resolution_w: int,
    coverage_width_per_m: float,
) -> float:
    """Distance Z where frame-average horizontal PPM equals the threshold.

    PPM(Z) = resolution_w / W(Z). For models where W grows linearly with Z
    (pinhole and equidistant fisheye coverage at the scene plane):
    W(Z) = coverage_width_per_m * Z, hence Z = res_w / (PPM * coverage_width_per_m).

    Args:
        required_ppm: Target pixels per meter (horizontal, averaged over frame width).
        resolution_w: Horizontal resolution in pixels.
        coverage_width_per_m: Scene width in meters at Z = 1 m (from geometry module).

    Returns:
        Distance in meters.
    """
    if coverage_width_per_m <= 0:
        raise ValueError("coverage_width_per_m must be positive")
    return resolution_w / (required_ppm * coverage_width_per_m)


def distance_for_ppm(
    required_ppm: float,
    resolution_w: int,
    sensor_width_mm: float,
    focal_length_mm: float,
) -> float:
    """Pinhole-only DORI distance (JVSG: W = Z * sensor_w / f).

    Prefer ``distance_for_coverage_ppm`` when using another lens model.
    """
    return (resolution_w * focal_length_mm) / (required_ppm * sensor_width_mm)


def dori_distances_from_coverage(
    resolution_w: int,
    coverage_width_per_m: float,
) -> dict[str, float]:
    """Compute DORI zone distances from horizontal coverage slope W/Z."""
    return {
        "detection_m": distance_for_coverage_ppm(
            DORI_DETECTION_PPM, resolution_w, coverage_width_per_m
        ),
        "observation_m": distance_for_coverage_ppm(
            DORI_OBSERVATION_PPM, resolution_w, coverage_width_per_m
        ),
        "recognition_m": distance_for_coverage_ppm(
            DORI_RECOGNITION_PPM, resolution_w, coverage_width_per_m
        ),
        "identification_m": distance_for_coverage_ppm(
            DORI_IDENTIFICATION_PPM, resolution_w, coverage_width_per_m
        ),
    }


def dori_distances(
    resolution_w: int,
    sensor_width_mm: float,
    focal_length_mm: float,
) -> dict[str, float]:
    """Compute DORI zone distances for rectilinear (pinhole) optics."""
    coverage_per_m = sensor_width_mm / focal_length_mm
    return dori_distances_from_coverage(resolution_w, coverage_per_m)
