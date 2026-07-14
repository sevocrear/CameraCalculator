# models/ — GLB эталонных объектов

Папка с мешами для 2D/3D-визуализации CameraCalculator.  
Документация проекта, навигация, Docker и зависимости — в [../README.md](../README.md).

Габариты объектов для расчёта пикселей (W×H×D, offsets, visual scale) задаются в  
[`../src/cctv_lens_calc/domain/reference_objects.py`](../src/cctv_lens_calc/domain/reference_objects.py) — не путать с размерами исходного GLB.

| Файл | Object id | В UI |
|------|-----------|------|
| `free_porsche_911_carrera_4s.glb` | `car` | Авто |
| `donut_2.0.glb` | `donut` | Пончик |
| `free_download_athletic_african_man_walking_223.glb` | `person` | Человек |
| `coca-cola_can__can_of_soda.glb` | `cola_can` | Банка Coca-Cola |
| `shopping_bag.glb` | `basket` | Корзина |

Статика отдаётся приложением с префикса `/models/…`.

---

## Credits

Исходники — Sketchfab (CC Attribution / CC BY-SA).

| Object id | Модель | Автор | License | Ссылка |
|-----------|--------|-------|---------|--------|
| `car` | (FREE) Porsche 911 Carrera 4S | [Lionsharp Studios](https://sketchfab.com/lionsharp) | CC BY-SA | [sketchfab](https://sketchfab.com/3d-models/free-porsche-911-carrera-4s-d01b254483794de3819786d93e0e1ebf) |
| `donut` | Donut 2.0 | [¡Jacques](https://sketchfab.com/iJacques) (`@iJacques`) | CC BY | [sketchfab](https://sketchfab.com/3d-models/donut-20-8d6cac74abfc4b408ec86c37661fa5a6) |
| `person` | Athletic African man walking 223 | [deep3dstudio](https://sketchfab.com/deep3dstudio) | CC BY | [sketchfab](https://sketchfab.com/3d-models/free-download-athletic-african-man-walking-223-f9a8e3b108f04e998815593f78f163b1) |
| `cola_can` | Coca-Cola Can / Can of Soda | [ForevereQ](https://sketchfab.com/ForevereQ) | CC BY | [sketchfab](https://sketchfab.com/3d-models/coca-cola-can-can-of-soda-a49763f3d67e4cd1bf7a41319535f4d0) |
| `basket` | Shopping Bag | [RavenBlox](https://sketchfab.com/RavenBlox) | CC BY | [sketchfab](https://sketchfab.com/3d-models/shopping-bag-e67edba7be6342888770ad7c3c0c6de9) |
