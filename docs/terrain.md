# Terrain, contact, and wheel-driven sand

The active ground path is `/Lunalab/Terrain/terrain_mesh`. The normal scene renders one height-grid mesh and collides with it as a static triangle mesh. Sand mode uses the same starting heights but replaces the rendered and colliding faces with small tiles that can be rebuilt under the wheels. This distinction matters: the rover can drive on a visible surface only when an appropriate collider also supports it.

```text
source DEM → transpose/crop/pad → 650 × 1000 height samples → USD terrain points/faces
    ├─ normal scene: one visible mesh + one static triangle-mesh collider
    └─ sand scene: baseline points + 176 visible/colliding tiles
                    wheel pose/spin/speed/contact → RutField → touched tile rebuild
```

## Elevation data and geometry

| Input or setting | Current value | Meaning |
| --- | --- | --- |
| Source DEM and mask | `assets/terrain/source/{dem,mask}.npy` | 998 × 652 source arrays; mask is retained as metadata, not used to cut elevation |
| Heightmap image | `assets/terrain/source/heightmap16.png` | Preserved source artifact; the Python generator reads the NumPy DEM |
| `width_m`, `length_m` | 10.0 m, 6.5 m | Nominal grid dimensions in `config/terrain.yaml` |
| `resolution_m` | 0.01 m/sample | 1 cm spacing; `round(length/resolution)` rows and `round(width/resolution)` columns |
| Resulting grid | 650 rows × 1000 columns | 650,000 vertices and 1,296,702 triangles; X/Y span between first and last samples is 9.99 × 6.49 m |
| `input_policy` | `transpose_then_crop_zero_pad` | Transpose to 652 × 998, crop two rows, pad two columns with zero height |
| `craters.enabled` | `false` | Optional seeded craters are an offline experiment, not part of the saved canonical DEM parity |
| `craters.seed`, `count` | 42, 20 | Repeatability and count when craters are enabled |

`terrain/generate.py` produces a compressed NPZ archive with vertices, faces, face-varying UVs, DEM, mask, and metadata. It does **not** edit a USD stage. Each grid cell becomes two triangles with the saved winding. The prior untransposed loader cropped the long source axis and introduced a flat 3.48 m zero-filled strip; the corrected canonical stage matches the transposed source. Zero padding at the remaining two columns is still an edge condition, so do not infer physical elevation outside the measured source area.

For a flat or smooth mobility experiment, create a separate candidate scene. The maintained generator here processes the DEM, optional seeded craters, or an offline wheel trace.

## Visible geometry and collision

| Property | Normal stage | Sand stage |
| --- | --- | --- |
| Visible surface | Original 650,000-point terrain mesh | 176 visible triangle-mesh tiles |
| Ground collision | `UsdPhysics.CollisionAPI` enabled on original mesh; `MeshCollisionAPI` approximation `none` | Original collision disabled; each tile has enabled static triangle-mesh collision |
| Original terrain faces | 1,296,702 | Removed in generated candidate; original points remain as undeformed reference |
| Rigid body on ground | Absent | Absent on tiles |
| Live edit | None in normal driving | Runtime rebuilds only tiles touched by wheel stamps |

`none` means PhysX uses the actual triangles for ground contact. A convex hull can bridge over depressions and make wheels appear to float. The seven placed rocks under `/package/rock*` intentionally use convex-hull colliders; they are rigid obstacles, not the height-grid ground. The composed stage marks `/World/Lab/Lab/CurvedWall/Cube_003` inactive after an earlier obstruction test. See [environment](environment.md).

## Scripts and safe workflows

| Script | Reads | Writes or checks | When to use |
| --- | --- | --- | --- |
| `terrain/generate.py` | Source DEM, mask, `config/terrain.yaml` | NPZ archive only | Reproduce heights, test optional craters, replay wheel CSV |
| `terrain/build_scene_candidate.py` | Canonical USD and source DEM | Separate corrected USD beside source | Rebuild DEM heights and seven placed-rock colliders for review; refuses an existing output |
| `terrain/validate.py` | Saved normal USD | Read-only audit | Check DEM orientation, topology, terrain collider, rocks, inactive obstruction prim |
| `terrain/repair.py` | Existing USD | Separate USD only with `--apply` | Narrow static terrain collider repair; does not modify source or create missing APIs |
| `terrain/build_sand_scene.py` | 55 kg candidate, optionally NPZ | Separate sand USD in same folder | Build visible/colliding tiles; `--overwrite` is explicit |
| `terrain/validate_sand_scene.py` | Sand USD | Read-only audit | Check tile count, visibility, collider settings, seams, and rut/berm bounds |
| `isaac/terrain/sand_runtime.py` | Open sand USD, wheel state, `config/terrain.yaml` | In-memory USD tile edits | Live deformation while the sand scene plays |

From the repository root, with the optional Python dependencies installed:

```powershell
py -m pip install -e ".[terrain,usd-audit]"
py terrain/generate.py --output work/terrain_rebuild.npz
py terrain/validate.py scenes/CAMERASYNCSSMOETIMES.usd
```

Use Isaac Sim's `python.bat` if standalone USD Python bindings are unavailable. To build or refresh the ignored sand candidate, close any open copy of that stage first:

```powershell
$isaacPython = 'C:\isaac-sim\_build\windows-x86_64\release\python.bat'
& $isaacPython terrain/build_sand_scene.py --overwrite
& $isaacPython terrain/validate_sand_scene.py
.\scripts\windows\start_rover_all.ps1 -SandDeformation
```

The builder copies the 55 kg candidate and keeps the output beside it so relative USD references still resolve. It does not change the source scene. An already-running Isaac Sim process prevents the launcher from attaching updated sand code; save any unrelated work and close that process before relaunching. Press **Play**, drive, and look for `AIAA_SAND_READY` and `AIAA_SAND_RUT` in the Isaac log. **Pause** keeps the current ruts; **Stop/Reset** restores the sand scene's starting surface by default and prints `AIAA_SAND_RESET`. The runtime also clears ruts from a previously saved sand candidate when it attaches, unless persistence is enabled. Set `persist_deformation_on_reset: true` only when intentionally keeping and saving deformed terrain. Closing and rebuilding with `--overwrite` also restores a clean generated scene; do not overwrite a sand stage whose saved ruts you intend to keep.

## Sand model parameters

The current model is empirical. It uses wheel position, heading, angular speed, travel speed, nearest ground hit, an estimated normal load, and elapsed simulation time. It rejects wheels over rocks or above the sand contact tolerance. It depresses a wheel-shaped footprint and adds a bounded side berm. It does not simulate individual grains, suspension load transfer, or independently measured soil shear/rolling resistance. The normal-load estimate is rover weight divided by four wheels.

With the default CPU physics mode, the runtime updates the visible mesh under each wheel but waits to rebuild that tile's collision mesh until all wheels have moved clear of it. This preserves turning during CPU simulation; removing and recreating a contacted collider every 0.2 seconds had reduced a three-second spin test from roughly 47° to 11°. A wheel therefore feels a new rut when it later re-enters that tile, rather than immediately while making it. The optional `-GpuPhysics` mode still rebuilds contacted tiles at the normal interval. Stop restores both visible and collision geometry by default.

| `config/terrain.yaml` key under `deformation` | Current value | Effect / reason to change |
| --- | ---: | --- |
| `tile_cells` | 64 | Cells per tile edge; smaller tiles reduce per-rebuild geometry but increase tile count |
| `update_interval_s` | 0.20 s | Time between wheel-state sampling and tile updates |
| `persist_deformation_on_reset` | `false` | Stop restores touched tiles to the scene's starting surface; `true` keeps ruts across Stop and allows intentional save/reload |
| `wheel_radius_m` | 0.098 m | Contact-height gate and wheel surface speed from spin; keep in parity with robot |
| `wheel_width_m` | 0.080 m | Lateral rut footprint |
| `contact_length_m` | 0.120 m | Longitudinal rut footprint |
| `reference_load_n` | 135 N | Load used to scale reference sinkage; close to nominal 55 kg/4 weight |
| `reference_sinkage_m` | 0.006 m | Conservative target depression at reference load before slip and time response |
| `pressure_exponent` | 1.1 | Nonlinear load-to-sinkage response |
| `maximum_sinkage_m` | 0.012 m | Upper bound on rut depth below the original DEM |
| `compaction_time_s` | 0.30 s | How quickly repeated contact approaches target depth |
| `slip_sinkage_gain` | 0.30 | Extra target depth when wheel surface speed and travel speed differ |
| `displaced_volume_fraction` | 0.15 | Portion of removed height added to side berms in the grid model |
| `maximum_berm_m` | 0.003 m | Upper bound on raised ground above the original DEM |
| `contact_tolerance_m` | 0.025 m | Extra clearance for accepting a wheel as near sand |
| `maximum_stamp_spacing_m` | 0.025 m | Interpolation spacing for long wheel steps to avoid rut gaps |

These numbers are provisional, chosen to avoid the visually excessive channels seen with the earlier 18 mm reference sinkage, 60 mm cap, and 20 mm berm cap. At the nominal 135 N wheel load, the new target is 6 mm without slip and at most 7.8 mm at full modeled slip; the 12 mm cap accommodates higher loads. The terrain texture and grazing light can make even shallow relief look dark and sharp. A physically grounded calibration needs measured wheel load, sinkage, slip, and traction on the intended sand. The [performance analysis](performance-analysis.md) measured roughly 2.8–3.0 cm ruts with the **previous** settings. A separate headless direct-wheel drive with the new defaults traveled about 0.58 m in three simulated seconds, made a 7.7 mm maximum rut, and returned to zero measured depth on Stop. GUI appearance and controller feel remain to be checked.

## Offline wheel-path replay

`terrain/generate.py --wheel-trace` accepts a CSV with `time_s,wheel,x_m,y_m,center_height_m,heading_rad,ground_speed_m_s,spin_rad_s,normal_load_n`. Positions and heights are in terrain-local metres. Each wheel needs an initial row, then later rows with strictly increasing time. Use an explicit output path so the default terrain archive is not replaced:

```powershell
py terrain/generate.py --wheel-trace work/wheels.csv --output work/deformed_terrain.npz
& $isaacPython terrain/build_sand_scene.py --archive work/deformed_terrain.npz --overwrite
& $isaacPython terrain/validate_sand_scene.py
```

This applies a prescribed path to the soil model; it does not simulate the rover following that path.

## Validation and terms

| Test | Expected result | First place to inspect on failure |
| --- | --- | --- |
| Normal terrain audit | 650,000 points, 1,296,702 triangles, one static triangle-mesh ground collider, seven placed-rock colliders | `terrain/validate.py`, USD collision settings |
| Sand scene audit | 176 visible/colliding tiles with matching shared edges and bounded heights | `terrain/validate_sand_scene.py`, builder version |
| Static wheel contact | Wheels rest on visible ground without lasting jitter | Ground approximation, mass, wheel shapes, overlapping colliders |
| Sand drive | Ruts follow contacted wheels and rover keeps moving | Runtime log, tile collision, wheel pose query, ROS command path |
| RGB/depth and `/scan` | Messages continue while ruts update | Camera/lidar graphs and the full-mesh update regression described in performance report |
| Pause then resume | Existing ruts remain and driving continues from them | Timeline state and runtime log |
| Stop then Play, default | Touched tiles return to baseline before a new drive | `AIAA_SAND_RESET`, tile heights, next contact |
| Intentional persistence | With `persist_deformation_on_reset: true`, Stop keeps ruts and a saved sand stage reloads them | Config value and saved tile heights |

**DEM** means a sampled elevation array. A **USD Mesh** is the points and triangular faces used for rendering. A **collision mesh** is the geometry used for physics contact. A **tile** is one small patch of the sand surface. A **rut** is the depression beneath a wheel, and a **berm** is the small raised edge beside it. A **dirty region** is the part of the height grid changed by a wheel stamp; only intersecting tiles are rebuilt.
