"""Reference object presets for pixel visualization.

``model_offset_x_m`` and ``model_offset_y_m`` move the physical object center
and therefore affect projection math. ``model_mesh_offset_*`` and
``model_visual_scale`` only align the rendered GLB silhouette.
"""

from dataclasses import dataclass
from enum import StrEnum


class ObjectOrientation(StrEnum):
    """How the object sits relative to the optical axis (−Z)."""

    UPRIGHT = "upright"
    TOP_DOWN = "top_down"


@dataclass(frozen=True)
class ReferenceObject:
    """Physical dimensions of a reference object."""

    id: str
    label: str
    width_m: float
    height_m: float
    depth_m: float
    cv_threshold_px: float
    orientation: ObjectOrientation = ObjectOrientation.UPRIGHT
    # Physical-center offsets used by projection math.
    model_offset_x_m: float = 0.0
    model_offset_y_m: float = 0.0
    # Local mesh correction after fit/recenter (rendering only).
    model_mesh_offset_x_m: float = 0.0
    model_mesh_offset_y_m: float = 0.0
    model_mesh_offset_z_m: float = 0.0
    # Rotation to bring GLB into the project's coordinate convention (Euler, radians).
    model_rotation_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Physical dimension multiplier used by the API and projected bbox.
    model_scale_mul: float = 1.0
    # Additional GLB-only scale after fitting to physical dimensions.
    model_visual_scale: float = 1.0


REFERENCE_OBJECTS: dict[str, ReferenceObject] = {
    "donut": ReferenceObject(
        id="donut",
        label="Пончик",
        width_m=0.10,
        height_m=0.10,
        depth_m=0.03,
        cv_threshold_px=64.0,
        orientation=ObjectOrientation.UPRIGHT,
        model_rotation_xyz=(-1.5707963267948966, 3.141592653589793, 0.0),
    ),
    "cola_can": ReferenceObject(
        id="cola_can",
        label="Банка",
        width_m=0.066,
        height_m=0.12,
        depth_m=0.066,
        cv_threshold_px=64.0,
        orientation=ObjectOrientation.UPRIGHT,
        # The GLB centroid sits above the bounding-box center.
        model_mesh_offset_y_m=-0.007,
    ),
    "basket": ReferenceObject(
        id="basket",
        label="Корзина",
        width_m=0.40,
        height_m=0.35,
        depth_m=0.25,
        cv_threshold_px=32.0,
        orientation=ObjectOrientation.UPRIGHT,
    ),
    "person": ReferenceObject(
        id="person",
        label="Человек",
        width_m=0.50,
        height_m=1.75,
        depth_m=0.30,
        cv_threshold_px=32.0,
        orientation=ObjectOrientation.UPRIGHT,
        # The GLB centroid sits slightly above its geometric center.
        model_mesh_offset_y_m=-0.000,
        model_mesh_offset_x_m=0.006,
    ),
    "car": ReferenceObject(
        id="car",
        label="Авто",
        width_m=1.9,
        height_m=1.298,
        depth_m=4.50,
        cv_threshold_px=32.0,
        orientation=ObjectOrientation.TOP_DOWN,
        model_mesh_offset_x_m=0.025,
        model_mesh_offset_y_m=0.020,
        model_scale_mul=1.0,
        # The silhouette occupies less than its rectangular physical AABB.
        model_visual_scale=1.45,
        # After flattening, the GLB already faces the negative Z direction.
        model_rotation_xyz=(0.0, 0.0, 0.0),
    ),
}


def get_object(object_id: str) -> ReferenceObject | None:
    """Return reference object by id."""
    return REFERENCE_OBJECTS.get(object_id)


def list_objects() -> list[ReferenceObject]:
    """Return all reference objects."""
    return list(REFERENCE_OBJECTS.values())
