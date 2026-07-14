# CameraCalculator

Веб-калькулятор CCTV-оптики: подбор матрицы, фокусного и типа оптики по FOV, покрытию, PPM/PPC/GSD, DORI (EN 62676-4) и размеру эталонного объекта в пикселях.

Поддерживаются **rectilinear (pinhole)** и **equidistant fisheye** (`r = f·θ`). UI: Three.js (3D-схема + 2D-кадр с bbox). Backend: FastAPI.

- UI: http://localhost:8088  
- Health: http://localhost:8088/health  
- OpenAPI: http://localhost:8088/docs  

---

## Requirements

| Слой | Версия / образ  |
|------|----------------------------------------------------------|
| **Python** | `>=3.12` (`requires-python` в `pyproject.toml`) |
| **Docker (хост)** | Docker `29.2.0`, Compose `v5.0.2` |
| **Base image** | `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` |
| **Runtime image** | ~102 MB (`cctv_lens_calc-app:latest`) |
| **Порт** | хост `8088` → контейнер `8000` |

### Runtime (из `uv.lock`)

| Пакет | Версия |
|-------|--------|
| fastapi | 0.139.0 |
| uvicorn | 0.49.0 |
| pydantic | 2.13.4 |
| starlette | 1.3.1 |

### Dev / тесты (extras `dev`)

| Пакет | Версия |
|-------|--------|
| pytest | 9.1.1 |
| httpx | 0.28.1 |
| hypothesis | 6.156.1 |
| playwright | 1.61.0 |

Источник истины по зависимостям: [`pyproject.toml`](pyproject.toml) + [`uv.lock`](uv.lock). Не держим отдельный `requirements.txt` — ставим через **uv** или Docker.

```bash
# локально
uv sync --all-extras

# только runtime
uv sync --frozen --no-dev
```

---

## Быстрый старт (Docker)

```bash
cd tools/cctv_lens_calc
docker compose up -d --build
docker compose ps          # app → healthy
docker compose down
```

Тесты (профиль `test`, сеть shared с app):

```bash
docker compose --profile test build test
docker compose --profile test run --rm test
```

Полный CI:

```bash
./scripts/ci.sh
```

### Разработка без Docker

```bash
uv sync --all-extras
uv run uvicorn cctv_lens_calc.api.main:app --reload --port 8000
uv run pytest -v
# UI-тесты (нужен живой сервер на BASE_URL, по умолчанию :8000):
BASE_URL=http://127.0.0.1:8000 uv run pytest -v -m ui
```

---

## Навигация по проекту

```
tools/cctv_lens_calc/
├── README.md                 ← этот файл
├── pyproject.toml            ← зависимости, pytest markers
├── uv.lock                   ← pinned versions
├── Dockerfile                ← multi-stage: builder / runtime / test
├── docker-compose.yml        ← app (:8088) + profile test
├── models/                   ← GLB эталонов + credits
│   └── README.md
├── scripts/                  ← CI-обёртки
├── src/cctv_lens_calc/
│   ├── api/                  ← FastAPI entry + routes
│   ├── domain/               ← математика и пресеты
│   └── web/static/           ← UI (HTML/CSS/JS, Three.js)
└── tests/                    ← unit / golden / Playwright
```

| Путь | Зачем |
|------|--------|
| `src/.../domain/calculator.py` | Оркестратор: FOV → coverage → PPM/GSD → DORI → object px |
| `src/.../domain/pinhole.py` | Rectilinear: FOV, coverage, object_pixels |
| `src/.../domain/fisheye.py` | Equidistant: f_eff из HFOV, FOV, coverage, pixels |
| `src/.../domain/dori.py` | EN 62676-4 пороги и дистанции от coverage |
| `src/.../domain/presets.py` | Размеры матриц (optical format) + пресеты камер |
| `src/.../domain/reference_objects.py` | Габариты объектов, offsets, `model_visual_scale` |
| `src/.../domain/models.py` | Pydantic-контракты API |
| `src/.../domain/projection.py` | 3D→2D точка (center_u/v) |
| `src/.../api/main.py` | Приложение FastAPI, static `/`, `/models` |
| `src/.../api/routes.py` | `/api/calculate`, `/api/presets/*`, `/health` |
| `web/static/js/app.js` | UI state, API, sync слайдеров |
| `web/static/js/scene3d.js` | 3D frustum / DORI / объекты |
| `web/static/js/viewport2d.js` | 2D кадр resolution W×H + bbox |
| `web/static/js/model_prep.js` | Fit GLB к W×H×D, visual scale |
| `web/static/js/help.js` | Подсказки «?» |
| `models/*.glb` | Меши эталонов (см. [models/README.md](models/README.md)) |
| `tests/fixtures/golden_cases.json` | Регрессия vs эталонные цифры / JVSG |

---

## Важные конфигурационные файлы

| Файл | Что крутить |
|------|-------------|
| **`domain/presets.py`** | `SENSOR_PRESETS` (мм активного сенсора), `CAMERA_PRESETS`, `CV_THRESHOLDS` |
| **`domain/reference_objects.py`** | Физические W/H/D, CV-порог px, mesh offsets, `model_visual_scale` |
| **`web/static/index.html`** | Разметка UI; cache-bust `?v=…` для CSS/JS |
| **`web/static/css/style.css`** | Тема, layout 100dvh, цвета DORI |
| **`docker-compose.yml`** | Порт `8088:8000`, healthcheck, profile `test` |
| **`Dockerfile`** | Python 3.12 + uv; targets `runtime` / `test` |
| **`pyproject.toml`** | зависимости, `tool.pytest` |
| **`tests/conftest.py`** | `BASE_URL` (default `http://127.0.0.1:8000`) |

Матан не хардкодить во фронте: цифры метрик и DORI всегда с `/api/calculate`.

---

## API

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/health` | liveness + checks |
| POST | `/api/calculate` | полный расчёт |
| GET | `/api/presets/sensors` | optical formats |
| GET | `/api/presets/cameras` | camera presets (+ expanded) |
| GET | `/api/presets/objects` | reference objects |
| GET | `/api/presets/cv_thresholds` | пороги px для CV |

`camera.sensor_format_id` **или** явные `sensor_width_mm` / `sensor_height_mm`.

---

## Формулы (кратко)

**Rectilinear**
- HFOV = 2·atan(sensor_w / 2f)  
- Coverage W = 2·Z·tan(HFOV/2)  
- PPM = resolution_w / W ··· GSD (mm/px) = 1000 / PPM  
- px_w = object_w · res_w · f / (Z · sensor_w)

**Equidistant fisheye**
- θ_max = (sensor_dim/2) / f → FOV = 2·θ_max  
- номинальный HFOV → f_eff = (sensor_w/2) / θ_max  
- DORI от покрытия: Z = res_w / (PPM_th · W_per_m)

**DORI (EN 62676-4), горизонтальные пороги**  
Detection 25 · Observation 62.5 · Recognition 125 · Identification 250 px/m

Сверка с [JVSG](https://www.jvsg.com/calculators/cctv-lens-calculator/): rectilinear расхождение **< 1%**.

| Кейс | Параметры | Ожидание |
|------|-----------|----------|
| JVSG baseline | 1/3", f=4mm, Z=10m | W=12.0m, PPM=160 |
| Close-up | 5.37mm, f=2.8, cola @ 0.45m | ~147×267 px |
| Wide fisheye | 160°, donut @ 0.3m | HFOV=160° |
| Mid range | f=2.8, basket @ 3m | ~134×117 px |
| 1/4" 6mm 5m | 1280px | W=3.0m, PPM=427 |

---

## 3D-модели

Кредиты и лицензии: [models/README.md](models/README.md).  
Габариты для матана — только в `reference_objects.py`, не в GLB.
