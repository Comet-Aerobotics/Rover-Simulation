# Terrain tools

This package owns offline elevation processing, scene-copy builders, validators, and the empirical rut field. The complete architecture, parameter table, and workflows are in [docs/terrain.md](../docs/terrain.md).

| File | Job | Changes a saved USD? |
| --- | --- | --- |
| `generate.py` | Transpose/crop/pad source DEM; generate vertices, triangles, UVs, metadata; optionally add craters or replay a wheel CSV | No; writes NPZ |
| `deformation.py` | Pure height-grid rut/berm model shared by offline replay and live Isaac runtime | No |
| `build_scene_candidate.py` | Copy canonical scene, refresh DEM heights, add seven placed-rock colliders | Yes, separate output only; refuses overwrite |
| `repair.py` | Narrow collider repair on an existing terrain mesh | Yes, separate output with `--apply` |
| `validate.py` | Audit normal terrain/rock geometry and colliders | No |
| `build_sand_scene.py` | Copy 55 kg candidate and make 176 visible/colliding sand tiles | Yes, separate output; explicit `--overwrite` |
| `validate_sand_scene.py` | Audit tile visibility, contact, seams, and height bounds | No |

The ground path is `/Lunalab/Terrain/terrain_mesh`. The standard grid is 650 × 1000 at 1 cm spacing; each cell yields two triangles. The normal collider is static with `physics:approximation = none`. Sand mode retains the original points as the baseline but renders and collides through tiles.

From the repository root:

```powershell
py -m pip install -e ".[terrain,usd-audit]"
py terrain/generate.py --output work/terrain_rebuild.npz
py terrain/validate.py scenes/CAMERASYNCSSMOETIMES.usd
```

Use Isaac Sim's `python.bat` to build/validate a sand stage if standalone USD bindings are unavailable. Keep outputs beside their source USD to preserve relative references, and do not overwrite a user-edited working scene. The runtime that changes tiles during Play lives in [`isaac/terrain/sand_runtime.py`](../isaac/terrain/sand_runtime.py).
