# Terrain pipeline and collider

The selected scene's `/Lunalab/Terrain/terrain_mesh` has one enabled static triangle-mesh collider (`physics:approximation = none`) and no rigid body. It contains 650,000 points and 1,296,702 triangles. Keep that terrain collider as a triangle mesh; do not add overlapping terrain colliders or apply a rigid body to the terrain.

Original `dem.npy`, `mask.npy`, and `heightmap16.png` are retained under `assets/terrain/source/`. The DEM and mask arrays are shaped 998×652, while the configured mesh grid is 650×1000. The previous loader copied the untransposed arrays into that grid, so it filled 348 columns (3.48 m) with zero-height vertices and cropped the long source axis. The corrected policy transposes both source arrays before fitting the configured grid. This retains almost all source coverage; only two columns are padded and two rows are cropped. The mask remains metadata and does not modify elevations.

`terrain/generate.py` transposes the source DEM and then fits it to the 1000×650 grid at 1 cm/sample. It retains the triangle winding and UV generation, and optional seed-42 craters remain disabled by default. The corrected heights intentionally differ from the old saved scene because its flat 3.48 m strip came from the axis mismatch.

`terrain/build_scene_candidate.py` can write a separate `scenes/CAMERASYNCSSMOETIMES_REBUILT_CANDIDATE.usd` copy without overwriting the canonical scene. It updates only the existing terrain points and applies convex-hull collision to the seven render meshes under `/package/rock*`. The rocks already had render meshes (some only 96 faces); those meshes lacked collision APIs. Separate detailed rocks under `/World/rock1`, `/World/rock3`, and `/World/rock4` already had collision, but they are misplaced above or beyond the terrain. The promoted canonical scene has been opened and visually reviewed in Isaac Sim.

From the repository root, install the optional tools and build/audit the candidate with:

```powershell
py -m pip install -e ".[terrain,usd-audit]"
py terrain/build_scene_candidate.py
py terrain/validate.py scenes/CAMERASYNCSSMOETIMES.usd
```

`terrain/validate.py` provides a read-only USD audit of DEM height orientation, terrain topology/collision, and the seven placed rock colliders. `terrain/repair.py` is explicitly opt-in, requires a separate output file in the source directory, and changes only the existing terrain collider's approximation/enabled state. It requires both existing collision APIs, refuses to synthesize missing colliders, and does not touch unrelated geometry.

The canonical composed stage retains a source opinion for `/World/Lab/Lab/CurvedWall/Cube_003` but marks the prim inactive. Therefore it does not participate in simulation, and the original geometry remains recoverable from the preserved source layer. This matches the user's deletion decision without broad wall-mesh edits or restoring the obstruction. The validator flags the prim only if it becomes active. Older scene candidates that still activate it are kept outside the focused project archive.
