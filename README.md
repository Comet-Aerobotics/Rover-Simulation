# AIAA Isaac Sim Rover

This repository runs a Jackal-based rover in the LunaLab scene with Isaac Sim 6.1, ROS 2 Humble teleoperation in WSL/Docker, an OAK-style RGB/depth camera, a VLP-16 lidar, and an optional wheel-driven sand-rut model. The USD scene owns the robot, environment, physics, sensors, and Action Graphs. Python and PowerShell tools build variants, launch the stack, and audit what is saved.

## System at a glance

```text
Controller → Windows USB/IP → WSL /dev/input/jsN → Docker joy_node → /joy
  → teleop_publisher → /cmd_vel → Isaac ROS 2 Bridge → drive Action Graph
  → four wheel joints → wheel/terrain contact

Terrain DEM → 1 cm mesh → visible ground + static collision
                                  ↘ optional sand tiles + live wheel ruts
OAK camera / lidar / robot pose → Isaac sensor graphs → ROS image, scan, TF, clock
```

| Scene | Purpose | Ground | Rover mass |
| --- | --- | --- | --- |
| `scenes/CAMERASYNCSSMOETIMES.usd` | Tracked canonical stage and normal launcher default | Static terrain mesh | Base link authors `physics:mass = 0`; do not treat that as a measured total mass |
| `scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd` | Handling comparison | Static terrain mesh | About 53.092 kg base plus four 0.477 kg wheels, totaling about 55 kg |
| `scenes/in work/CAMERASYNCSSMOETIMES_55KG_SAND_CANDIDATE.usd` | Generated, ignored sand test stage | 176 visible/colliding rut tiles | Built from the 55 kg candidate |

The canonical stage is Z-up and uses one meter per USD unit. The saved physics scene uses GPU dynamics and GPU broadphase at 60 physics steps per second. A headless performance comparison favored CPU dynamics with MBP for this single-rover scene, but that change has not been promoted to the tracked scene. See [performance analysis](docs/performance-analysis.md).

## Run the simulation

From PowerShell in the repository root:

```powershell
.\scripts\windows\start_rover_all.ps1 -Mode Diagnostics
.\scripts\windows\start_rover_all.ps1
```

The first command inspects WSL, Docker, and controller visibility. The second starts or reuses the ROS container and opens Isaac Sim if it is not already running. The current working launcher also offers a split-controller pair when two joystick devices appear; that newer path needs its own live acceptance. Press **Play** in Isaac Sim before testing motion or sensor topics. An already-running Isaac Sim process keeps its current scene and ROS environment; the launcher will not replace an open stage.

To test wheel-driven ground deformation, save and close any open Isaac Sim stage, then run:

```powershell
.\scripts\windows\start_rover_all.ps1 -SandDeformation
```

The sand scene must first exist. Build it with Isaac Sim's `python.bat` if missing, or use `--overwrite` to regenerate it after closing that scene; the exact commands are in [terrain](docs/terrain.md). Stop only this project's teleop nodes with `.\scripts\windows\stop_rover.ps1`. The stop script leaves Isaac Sim and containers open.

## Where to learn or change a subsystem

| Need | Read first | Authoritative file or prim |
| --- | --- | --- |
| Scene layout, ownership, and variants | [Architecture](docs/architecture.md), [scenes](scenes/README.md) | Saved USD stage |
| Elevation, rocks, contact, and sand ruts | [Terrain](docs/terrain.md), [environment](docs/environment.md) | `config/terrain.yaml`, `/Lunalab/Terrain/terrain_mesh` |
| Rover mass, wheels, and drive mechanics | [Rover](docs/rover.md), [Action Graphs](docs/isaac/action-graph.md) | `/jackal`, `/jackal/ActionGraph` in USD |
| RGB/depth, lidar, TF, and clock | [Sensors](docs/sensors.md) | Camera/lidar prims and USD graphs |
| Controller mapping and ROS topics | [ROS 2](docs/ros2.md) | `config/{joy,controller,ros}.yaml`, `cometbot_control` |
| Startup and shutdown | [Launch guide](docs/setup/launch.md), [Windows scripts](scripts/windows/README.md) | `scripts/windows/` |
| Tests, performance, and unresolved behavior | [Tests](tests/README.md), [performance](docs/performance-analysis.md), [known issues](docs/known-issues.md) | Validators and recorded measurements |

Generated scenes, ROS build outputs, and `work/` scratch files are not source of truth. The modified `in work` 55 kg scene may contain local unsaved or uncommitted edits; review it before replacing or committing it. Third-party asset provenance is in [source manifest](docs/source-manifest.md) and [ownership notes](docs/ownership-and-migration.md).
