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

## Wheel-driven sand ruts (opt in)

The sand candidate starts from `scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd`. It retains the original terrain's 650,000 points as an undeformed height reference, removes that mesh's faces, and disables its collider. In its place, 176 visible static triangle-mesh tiles supply both rendering and collision. The runtime samples each wheel's position, heading, angular speed, travel speed, and the nearest physics surface. A bounded empirical soil model lowers the terrain beneath loaded wheels and builds small side berms. Only touched tiles are rebuilt, so the visible ground and rover contact follow the same rut. Rocks remain rigid, and a wheel whose nearest surface is a rock does not stamp sand.

The current normal load is the 55 kg rover's weight divided equally among four wheels. It is an estimate; suspension load transfer, soil shear, rolling resistance, and individual grains are not modeled. The values in `config/terrain.yaml` are provisional and should be calibrated against wheel sinkage and traction measurements from the intended sand. The model limits rut depth to 6 cm. The update interval is 0.2 s and tiles span 64 grid cells; adjust these only after checking runtime cost and collision behavior.

Build and validate a separate sand scene using Isaac Sim's Python (set `$isaacPython` to the installed `python.bat`):

```powershell
$isaacPython = 'C:\isaac-sim\_build\windows-x86_64\release\python.bat'
& $isaacPython terrain/build_sand_scene.py
& $isaacPython terrain/validate_sand_scene.py
```

The builder refuses to overwrite an existing candidate unless passed `--overwrite`. Existing sand candidates built with the older full-mesh visual path must be rebuilt. The generated scene is ignored by Git. Save and close any existing Isaac Sim scene before launching this candidate; the launcher will leave an already running Isaac Sim process untouched.

```powershell
./scripts/windows/start_rover_all.ps1 -SandDeformation
```

The tile update path passed isolated headless ROS driving and RGB/depth/scan delivery under both CPU and GPU physics; see `docs/performance-analysis.md`. Controller handling and visible rut quality in the GUI still need an operator check. Sand edits exist in the open stage; save the candidate scene if the ruts should persist. On reopening, the runtime restores rut heights from the saved tiles while keeping the original points as the undeformed reference. To reset the surface, close the candidate and rerun the builder with `--overwrite`. The original 55 kg scene and canonical scene are not changed by the builder.

For an offline replay, use a CSV with columns `time_s,wheel,x_m,y_m,center_height_m,heading_rad,ground_speed_m_s,spin_rad_s,normal_load_n`. Positions and heights are in the terrain mesh's local frame and SI units. Each wheel needs an initial row and later rows with increasing times; only later rows stamp the path. The generator uses the same soil model as the runtime:

```powershell
py terrain/generate.py --wheel-trace work/wheels.csv --output work/deformed_terrain.npz
& $isaacPython terrain/build_sand_scene.py --archive work/deformed_terrain.npz --overwrite
& $isaacPython terrain/validate_sand_scene.py
```

`--wheel-trace` requires an explicit output path to protect the default terrain archive. An offline replay represents a prescribed wheel path; it does not simulate the vehicle following that path.
