/** Подсказки к параметрам и метрикам (RU). */

const HELP = {
  cameraPreset:
    'Готовый профиль камеры: сенсор, разрешение, фокусное и тип оптики.',
  lensType:
    'Rectilinear — обычная оптика (pinhole). Fisheye equidistant — «рыбий глаз» с проекцией r = f·θ.',
  fisheyeFov:
    'Номинальный горизонтальный угол обзора fisheye в градусах. По нему калибруется эффективное фокусное.',
  sensorFormat:
    'Optical format (Type) матрицы в дюймах — как в даташитах камер. Диагональ Type ≈ 1.5× реальной; в расчёт идут активные W×H в мм из таблицы.',
  sensorDimsMm:
    'Активная область матрицы в мм (ширина × высота), которая используется в формулах FOV и PPM.',
  resW: 'Горизонтальное разрешение кадра в пикселях. Используется для PPM и ширины bbox объекта.',
  resH: 'Вертикальное разрешение кадра в пикселях. Используется для высоты bbox объекта.',
  focal:
    'Фокусное расстояние в мм. Для fisheye это эффективное значение, вычисленное из номинального HFOV.',
  distance:
    'Расстояние от камеры до плоскости сцены по оптической оси (метры). Задаёт ширину покрытия и PPM.',
  mountHeight:
    'Высота установки камеры над полом в 3D-схеме (метры). Влияет только на визуализацию, не на расчёт FOV.',
  objectDistance:
    'Расстояние от камеры до эталонного объекта (метры). Определяет размер объекта в пикселях.',
  objectOffsetY:
    'Смещение центра объекта по Y относительно камеры (метры). Положительное — выше точки установки камеры.',
  objectOffsetX:
    'Боковое смещение центра объекта (метры). Положительное — вправо в кадре.',
  metricHfov: 'Horizontal Field of View — горизонтальный угол обзора в градусах.',
  metricVfov: 'Vertical Field of View — вертикальный угол обзора в градусах.',
  metricDfov:
    'Diagonal Field of View — угол обзора по диагонали сенсора. У fisheye при широком HFOV может превышать 180° (угол кадра дальше от оси, чем край по ширине).',
  metricCoverage:
    'Ширина × высота пересечения поля зрения с плоскостью перед камерой. При FOV ≥ 180° ограниченного пересечения нет — показывается N/A.',
  metricPpm:
    'Pixels Per Meter — пикселей на метр по горизонтали на выбранном расстоянии. Чем выше, тем детальнее картинка.',
  metricPpc: 'Pixels Per Centimeter — пикселей на сантиметр (PPM / 100).',
  metricGsd:
    'Ground Sample Distance — миллиметров на один пиксель на выбранном расстоянии (GSD = 1000 / PPM). Меньше = лучше детализация.',
  metricObjectPx:
    'Сколько пикселей занимает выбранный объект в кадре (ширина × высота bbox по центру).',
  metricCvPass:
    'Достаточно ли пикселей для CV-порога (детектор / эмбеддер). Зелёный — хватает, красный — мало.',
  doriDet: 'DORI Detection (25 px/m, EN 62676-4). Для fisheye это приближённая оценка по средней плотности кадра.',
  doriObs: 'DORI Observation (62.5 px/m) — макс. расстояние для наблюдения характеристик.',
  doriRec: 'DORI Recognition (125 px/m) — макс. расстояние для узнавания класса объекта.',
  doriId: 'DORI Identification (250 px/m) — макс. расстояние для идентификации (лицо, номер).',
};

function initTooltips() {
  document.querySelectorAll('[data-help]').forEach((el) => {
    if (el.querySelector('.tip-bubble')) return;
    const key = el.getAttribute('data-help');
    const text = HELP[key];
    if (!text) return;
    el.classList.add('has-tip');
    if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '0');
    const tip = document.createElement('span');
    tip.className = 'tip-bubble';
    tip.textContent = text;
    el.appendChild(tip);
  });
}
