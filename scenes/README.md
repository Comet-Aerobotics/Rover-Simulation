# USD scene variants

The saved USD stage determines actual prim transforms, collision APIs, masses, sensors, lights, and Action Graphs. Select a variant deliberately and record its name with every test result. The [architecture guide](../docs/architecture.md) explains process ownership.

| Stage | Status | Difference and use |
| --- | --- | --- |
| `CAMERASYNCSSMOETIMES.usd` | Tracked canonical scene and normal launcher default | Local VLP-16 Jackal, corrected DEM orientation, seven placed-rock colliders, static ground |
| `in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd` | Tracked working candidate; may have local modifications | Explicit roughly 55 kg rover mass for settling/handling comparison; user-confirmed controller motion applies here |
| `in work/CAMERASYNCSSMOETIMES_55KG_SAND_CANDIDATE.usd` | Generated, Git-ignored candidate | Visible/colliding terrain tiles and opt-in live rut runtime; rebuild with `terrain/build_sand_scene.py` |

The sand builder requires its output beside the 55 kg source because USD asset references are relative. Do not overwrite the working 55 kg candidate to make sand. Sand edits are in the open stage during Play; save the generated candidate if ruts should persist. An already-running Kit process will not switch stages when the launcher is called again. See [launch](../docs/setup/launch.md) and [terrain](../docs/terrain.md).
