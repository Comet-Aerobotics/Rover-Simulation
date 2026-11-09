# LunaLab environment and obstacles

The USD stage composes LunaLab structures, terrain, placed rocks, materials, cameras, and lights around the rover. The environment gives camera and lidar their visible geometry and gives PhysX obstacle colliders. A render mesh and a collider may differ, so an object can be seen without blocking the rover or can block it while hidden.

## Scene groups

| Group | Saved location or asset | Role |
| --- | --- | --- |
| Ground | `/Lunalab/Terrain/terrain_mesh` | Elevation and primary rover contact; see [terrain](terrain.md) |
| Lab structures | `/World/Lab/*`, project-local `assets/environments/lunalab/USD_Assets/lunalab/` | Walls, doors, pillars, curtains, grills, and related visual/physical features |
| Placed rocks | Seven meshes under `/package/rock*` | Obstacles on the terrain; each has a convex-hull collider in the canonical scene |
| Other rock assets | `/World/rock1`, `/World/rock3`, `/World/rock4` | Detailed meshes with collision, but earlier audits found them above or beyond the active terrain area |
| Materials and maps | `assets/environments/lunalab/Textures/`, `assets/materials/` | Visual appearance; missing textures can affect camera images without changing contact |
| Lighting | Six ceiling cylinder lights and one projector disk light | Affects viewport and RGB rendering cost and appearance |
| Fixed inspection cameras | `/World/Cameras/{BackView,TopView,FrontView}` | Operator views, separate from the rover OAK ROS stream |

The placed rock colliders use `convexHull`; that is appropriate for coarse rigid obstacles but does not preserve every cavity in a render mesh. The ground itself uses `physics:approximation = none` for triangle-mesh contact. Do not apply a convex hull to the irregular ground: it can bridge depressions and make the rover appear to float. The saved stage also has collider-enabled doors, a pillar, a window wall, and `/World/Lab/Grills/SandWall/Cube_002`.

The earlier invisible obstruction was traced to `/World/Lab/Lab/CurvedWall/Cube_003`, which the canonical composed stage marks inactive. Its source opinion remains recoverable. The separate SandWall collider was not the confirmed cause. If an obstacle reappears, identify its world-space location and collision status before disabling a larger group.

## Source asset map

| Source location | Contents and use |
| --- | --- |
| `assets/environments/configuration/lunarenvironment_{base,physics,sensor}.usd` | Referenced room configuration layers; inspect the composed stage because stronger scene opinions can override a source layer. |
| `assets/environments/lunalab/USD_Assets/lunalab/` | Modular walls, doors, curtains, grills, and other room geometry. |
| `assets/environments/lunalab/USD_Assets/rocks/lunar_rocks/` | Lower and higher detail USDZ rock families. |
| `assets/environments/lunalab/USD_Assets/rocks/lunalab_rocks/` | Detailed `rock1`, `rock3`, and `rock4` USD models with local diffuse and normal maps. |
| `assets/environments/lunalab/USD_Assets/rocks/apollo_rocks/` | Converted Apollo rock model with its image texture. |
| `assets/environments/lunalab/Textures/` | `Sand`, `GravelStones`, `BlackPaint`, `BlackIron`, `BlackBrick`, `ClothBlack`, `Glass`, and projector material resources. These control appearance, not collision. |

Isaac Sim supplies the built-in `OmniPBR.mdl` shader; it is not copied under `assets/materials/`. The project-local Black Matte normal-map default correction and third-party asset attribution are recorded in [third-party notices](../assets/THIRD_PARTY_NOTICES.md).

## What to change for an experiment

| Goal | Change in a candidate scene | Check after reload |
| --- | --- | --- |
| Test a route around rocks | Move or disable one placed rock at a time | Visual location, collider location, rover path, lidar return |
| Repair a missing rock contact | Inspect the specific `/package/rock*` mesh CollisionAPI | No duplicate overlapping rock collider |
| Test lighting cost | Disable one light group in memory | RGB exposure/visibility and frame time, with physics unchanged |
| Compare ground behavior | Select canonical, 55 kg, or generated sand candidate | Correct scene name, terrain collider mode, wheel response |
| Diagnose an invisible barrier | Audit active colliders and their bounds | Confirm a real collider intersects the rover path; bounds alone are screening evidence |

The room assets are project-local copies with separate license and provenance records. Keep relative USD references intact when copying a stage. Use [source manifest](source-manifest.md) and [asset README](../assets/environments/lunalab/README.md) for ownership. The operator should save a new candidate before altering environment geometry; the canonical stage should change only after the behavior is reviewed.
