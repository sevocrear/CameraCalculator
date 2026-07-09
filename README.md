# CCTV Lens Calculator

Подбор камеры для проекта «Прозрачный магазин»: FOV, PPM/PPC, DORI-зоны, пиксели на эталонном объекте. Rectilinear + equidistant fisheye.

## Запуск (Docker)

```bash
cd tools/cctv_lens_calc
docker compose up -d --build
```

- UI: http://localhost:8088 (порт 8088 — чтобы не конфликтовать с Traefik на 8080)
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
| Касса | sensor 5.37mm, f=2.8, cola @ 0.45m | ~147×267 px |
| Полка fisheye | 160°, donut @ 0.3m | HFOV=160° |
| Стеллаж | f=2.8, basket @ 3m | ~134×117 px |
| 1/4" 6mm 5m | 1280px | W=2.67m, PPM=480 |

Расхождение с JVSG на rectilinear: **< 1%**.

## Проверено вручную

1. Касса + cola_can @ 0.5 m (Optimus P012)
2. shelf_usb_fisheye + donut @ 0.3 m
3. optimus_p042 + basket @ 3 m

## API

- `GET /health`
- `POST /api/calculate`
- `GET /api/presets/{sensors,cameras,objects,cv_thresholds}`

## Формулы

- HFOV = 2·atan(sensor_w / 2f)
- Coverage W = 2·Z·tan(HFOV/2)
- PPM = resolution_w / W
- px_w = object_w · res_w · f / (Z · sensor_w)
- Fisheye: r = f·θ

Fisheye: пиксели на оптической оси; на краях кадра плотность ниже.
