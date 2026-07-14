# Bundled GLB models

These files provide reference-object silhouettes for the CameraCalculator UI.
The application serves them under `/models/`.

| Bundled file | Object ID | UI object |
|---|---|---|
| `free_porsche_911_carrera_4s.glb` | `car` | Авто |
| `donut_2.0.glb` | `donut` | Пончик |
| `free_download_athletic_african_man_walking_223.glb` | `person` | Человек |
| `coca-cola_can__can_of_soda.glb` | `cola_can` | Банка |
| `shopping_bag.glb` | `basket` | Корзина |

Physical dimensions, offsets, and visual scaling are configured in
[`src/cctv_lens_calc/domain/reference_objects.py`](../src/cctv_lens_calc/domain/reference_objects.py).
The source mesh dimensions are not calculation inputs.

For fisheye views, the rendered 2D GLB silhouette is schematic. The projected
bounding box returned by the calculation API is authoritative.

## Credits

| Work | Author | License | Source |
|---|---|---|---|
| “(FREE) Porsche 911 Carrera 4S” | [Lionsharp Studios](https://sketchfab.com/lionsharp) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | [Sketchfab](https://sketchfab.com/3d-models/free-porsche-911-carrera-4s-d01b254483794de3819786d93e0e1ebf) |
| “Donut 2.0” | [¡Jacques](https://sketchfab.com/iJacques) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [Sketchfab](https://sketchfab.com/3d-models/donut-20-8d6cac74abfc4b408ec86c37661fa5a6) |
| “Athletic African man walking 223” | [deep3dstudio](https://sketchfab.com/deep3dstudio) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [Sketchfab](https://sketchfab.com/3d-models/free-download-athletic-african-man-walking-223-f9a8e3b108f04e998815593f78f163b1) |
| “Coca-Cola Can / Can of Soda” | [ForevereQ](https://sketchfab.com/ForevereQ) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [Sketchfab](https://sketchfab.com/3d-models/coca-cola-can-can-of-soda-a49763f3d67e4cd1bf7a41319535f4d0) |
| “Shopping Bag” | [RavenBlox](https://sketchfab.com/RavenBlox) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [Sketchfab](https://sketchfab.com/3d-models/shopping-bag-e67edba7be6342888770ad7c3c0c6de9) |

The bundled files have no intentional geometry changes; the application scales
and orients them at runtime. Product names may be trademarks of their owners.

Complete third-party notices are in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). CameraCalculator source is
covered by [LICENSE](../LICENSE). See the [project README](../README.md) for
setup, API, and test instructions.
