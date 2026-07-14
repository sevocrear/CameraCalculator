# CameraCalculator

Веб-калькулятор CCTV-оптики: FOV, покрытие, PPM/PPC/GSD, DORI-зоны (EN 62676-4), размер эталонного объекта в пикселях. Поддерживаются rectilinear (pinhole) и equidistant fisheye.

## Запуск (Docker)

```bash
cd tools/cctv_lens_calc
docker compose up -d --build
```

- UI: http://localhost:8088
- Health: http://localhost:8088/health
- Статус: `docker compose ps` → `app` **healthy**

```bash
docker compose down
```

## Тесты

```bash
docker compose --profile test run --rm test
```

Полный CI:

```bash
./scripts/ci.sh
```

## Разработка (опционально)

```bash
uv sync --all-extras
uv run uvicorn cctv_lens_calc.api.main:app --reload --port 8000
uv run pytest -v
```

## Golden cases vs JVSG

Сверка с [JVSG Lens Calculator](https://www.jvsg.com/calculators/cctv-lens-calculator/):

| Кейс | Параметры | Ожидание |
|------|-----------|----------|
| JVSG baseline | 1/3", f=4mm, Z=10m | W=12.0m, PPM=160 |
| Close-up object | sensor 5.37mm, f=2.8, cola @ 0.45m | ~147×267 px |
| Wide fisheye | 160°, donut @ 0.3m | HFOV=160° |
| Mid range | f=2.8, basket @ 3m | ~134×117 px |
| 1/4" 6mm 5m | 1280px | W=3.0m, PPM=427 |

Расхождение с JVSG на rectilinear: **< 1%**.

## API

- `GET /health`
- `POST /api/calculate` — `camera.sensor_format_id` (optical format) или `sensor_width_mm` / `sensor_height_mm`
- `GET /api/presets/{sensors,cameras,objects,cv_thresholds}`

## Формулы

**Rectilinear (pinhole):**
- HFOV = 2·atan(sensor_w / 2f)
- Coverage W = 2·Z·tan(HFOV/2)
- PPM = resolution_w / W
- GSD (mm/px) = 1000 / PPM
- px_w = object_w · res_w · f / (Z · sensor_w)

**Equidistant fisheye:**
- θ_max = (sensor_dim / 2) / f → FOV = 2·θ_max
- при заданном номинальном HFOV: f_eff = (sensor_w / 2) / θ_max
- Coverage: луч края = Z·tan(θ_max), с ограничением для сверхшироких углов
- DORI считается через покрытие: Z = res_w / (PPM_threshold · W_per_m)

**DORI (EN 62676-4), горизонтальные пороги:**
- Detection 25 px/m · Observation 62.5 · Recognition 125 · Identification 250

## 3D-модели объектов

Кредиты авторам GLB — в [models/README.md](models/README.md).
