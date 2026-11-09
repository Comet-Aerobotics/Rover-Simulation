# Simulation architecture and ownership

The saved USD stage is the center of the simulation. It composes the LunaLab environment, terrain, local Jackal asset, physics scene, cameras, lidar, render products, lights, and OmniGraph Action Graphs. The Windows launcher selects a stage and prepares ROS; it does not regenerate the robot or its graphs. WSL/Docker runs joystick acquisition and Joy-to-Twist conversion. Sand mode adds a runtime that changes terrain tile geometry while Isaac Sim plays.

```text
Windows USB controller                 Isaac Sim on Windows
       │                                     ↑ /cmd_vel (ROS 2 Bridge)
       ▼                                     │
usbipd → WSL /dev/input/jsN → Docker ROS 2 Humble
                         /joy → teleop_publisher

USD stage: LunaLab + terrain + Jackal + camera + lidar + physics + graphs
       ├─ wheel contact and rover motion
       ├─ optional sand tile deformation
       └─ image, depth, scan, TF, odometry, clock → ROS 2
```

## Source of truth by concern

| Concern | Owner | Important location | Change procedure |
| --- | --- | --- | --- |
| Scene hierarchy and prim transforms | USD | `scenes/CAMERASYNCSSMOETIMES.usd` | Make a candidate scene; inspect composed references before promotion |
| Rover articulation, colliders, and graphs | USD plus referenced Jackal asset | `/jackal`, `assets/robots/jackal/` | Validate wheel joints and graph connections in the composed stage |
| Elevation source and offline processing | Source arrays and Python | `assets/terrain/source/`, `terrain/generate.py` | Generate an archive; compare it to the saved mesh before editing a stage |
| Static terrain and placed rocks | USD | `/Lunalab/Terrain/terrain_mesh`, `/package/rock*` | Run `terrain/validate.py` after scene changes |
| Live sand response | Python plus generated USD | `terrain/deformation.py`, `isaac/terrain/sand_runtime.py` | Build and validate a separate sand scene |
| Joystick mapping | ROS package and YAML | `ros2/cometbot_ws/src/cometbot_control/`, `config/joy.yaml`, `config/controller.yaml` | Run mapping tests and check live Joy/Twist values |
| Camera, lidar, TF, and clock publication | USD Action Graphs | `/ActionGraph`, `/jackal/ROS2_Graph/*` | Inspect graph and verify actual messages during Play |
| WSL/Docker and Isaac startup | PowerShell, Compose, Python hook | `scripts/windows/`, `docker/`, `isaac/diagnostics/open_scene_on_start.py` | Use Diagnostics before Start; inspect process environment if Kit is already open |

The YAML files record project settings and parity targets; some geometry and limits are authored in USD and must be checked there. There is no second project-owned graph or controller implementation outside the saved USD. `legacy/archived_scripts/` and the adjacent source archive preserve older approaches; they are not launch dependencies.

## Scene and runtime boundaries

| Boundary | Practical consequence |
| --- | --- |
| Canonical versus 55 kg candidate | A controller test in the candidate does not prove canonical mass or handling; use the scene name in reports. |
| Visible mesh versus collision | A surface can render without supporting a wheel. Visibility and collision are separate USD properties. |
| ROS topic versus end-to-end behavior | A publisher proves that a node exists; verify subscribers, a nonzero command, and rover motion separately. |
| Saved USD versus open Kit stage | Isaac may migrate nodes or hold unsaved edits in memory. Inspect or save intentionally before rebuilding or reopening. |
| Headless benchmark versus GUI | Headless frame times measure relative costs; the operator viewport, GPU contention, and controller feel need GUI checks. |

See [scene variants](../scenes/README.md), [ROS flow](ros2.md), and [launch](setup/launch.md).
