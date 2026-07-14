"""Reference object presets for pixel visualization.

Ориентации относительно камеры, смотрящей вдоль −Z (ось на центр объекта):
  - upright: объект «лицом» к камере, высота вдоль +Y (банка, человек, корзина, пончик)
  - top_down: объект лежит плашмя (авто как прямоугольник W×H)

Смещения:
  - model_offset_y_m / model_offset_z_m — сдвиг *физического центра* объекта (влияет на математику
    проекции и позицию в 3D/2D). model_offset_z_m — это сдвиг по X (влево/вправо в кадре).
  - model_mesh_offset_* — локальная поправка GLB после подгонки bbox (только визуализация,
    не меняет width_px/height_px).
  - model_scale_mul — множитель физ. габаритов для матана (W/H/D и bbox в px).
  - model_visual_scale — доп. масштаб только GLB после fitToDims (не меняет width_px/height_px).
"""

from dataclasses import dataclass
from enum import Enum


class ObjectOrientation(str, Enum):
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
    # Сдвиг физического центра (метры) — участвует в pinhole-математике.
    model_offset_y_m: float = 0.0
    model_offset_z_m: float = 0.0  # семантика: сдвиг по X (влево/вправо)
    # Локальная поправка меша после fit/recenter (только рендер).
    model_mesh_offset_x_m: float = 0.0
    model_mesh_offset_y_m: float = 0.0
    model_mesh_offset_z_m: float = 0.0
    # Rotation to bring GLB into the project's coordinate convention (Euler, radians).
    model_rotation_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Масштаб физ. размеров для API/bbox (умножает width/height/depth в calculator).
    model_scale_mul: float = 1.0
    # Масштаб только GLB-силуэта после fit к W×H×D (визуализация; 1.0 = без доп. увеличения).
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
        label="Банка Coca-Cola",
        width_m=0.066,
        height_m=0.12,
        depth_m=0.066,
        cv_threshold_px=64.0,
        orientation=ObjectOrientation.UPRIGHT,
        # GLB: центроид выше bbox-центра → визуально «сидит» на оси, bbox выше.
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
        # GLB: центроид ~7 см выше геом. центра bbox.
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
        # Силуэт GLB меньше прямоугольного AABB — чуть раздуваем только меш.
        model_visual_scale=1.45,
        # После flatten GLB уже смотрит в −Z; π разворачивал задом.
        model_rotation_xyz=(0.0, 0.0, 0.0),
    ),
}


def get_object(object_id: str) -> ReferenceObject | None:
    """Return reference object by id."""
    return REFERENCE_OBJECTS.get(object_id)


def list_objects() -> list[ReferenceObject]:
    """Return all reference objects."""
    return list(REFERENCE_OBJECTS.values())
