# Focused simulation inventory

**Updated:** 2026-11-05 | **Scope:** this LunaLab/Jackal simulation and its Stadia-to-ROS-to-Isaac control path.

The detailed responsibility-to-file audit is [ownership-and-migration.md](ownership-and-migration.md). Full initial repository intake, earlier scene revisions, and generated tooling/build outputs are retained outside the focused project in `../AIAA-Isaac-Sim-Rover-source-archive/`. The active tree contains the canonical local-Jackal scene dependency closure, relevant runtime code/configuration, and specifically relevant archived scripts. `work/` and ROS `build/`, `install/`, and `log/` are intentionally absent from the source tree; their preserved copies are in the adjacent archive.

## Authoritative system

| Component | Active source | Observed status |
|---|---|---|
| Stage | `scenes/CAMERASYNCSSMOETIMES.usd` (canonical); earlier scene revisions removed from this project | Canonical stage is Z-up, 1 m/unit, uses the local VLP-16 Jackal, corrected terrain orientation, and placed-rock colliders. It was opened/rendered in Isaac Sim 6.1 after terrain and rock changes; the user reviewed the result visually. |
| Terrain | `assets/terrain/source/` (hash-verified copy of OmniLRS `Terrain_lidar01`), `config/terrain.yaml`, `terrain/` | Canonical scene has 650,000 points, 1,296,702 triangles, one static terrain collider, and convex-hull colliders on all seven placed rocks. The corrected mesh matches the transposed DEM. `Terrain_lidar02` is archived and not referenced by this scene. |
| Rover/graph | `/jackal` and `/jackal/ActionGraph` in `scenes/CAMERASYNCSSMOETIMES.usd` | Canonical scene opened and rendered in Isaac Sim 6.1, exposes four wheel DOFs, and produced a measured static wheel-terrain contact. Powered motion and contact stability remain open. |
| Camera | `/ActionGraph` in selected scene; imported enclosure at `assets/robots/camera/` | 640×400 depth render product; `/oak_d/depth`, active `oak_d/camera_info` helper, `oak_d_optical_frame`; output messages remain unverified. |
| ROS | `ros2/cometbot_ws/src/cometbot_control/` and `config/{joy,controller,ros}.yaml` | Humble package builds; live legacy nodes and Stadia device observed. Six mapping tests pass. |
| Docker | `docker/` | Humble image builds; new service is separate from active `cometbot_dev`, and DDS profile has no fixed initial peer. |

## Exact open dependencies/limitations

- The canonical scene uses the project-owned VLP-16 Jackal asset and matching graph joint names.
- The wall material's stale UI default was corrected to the existing normal map referenced by its MDL definition.
- Earlier scene revisions with remote Jackal references or the terrain axis mismatch were removed from the active project. Source snapshots remain in the adjacent archive.
- The former default scene contained a zero-padded 3.48 m terrain strip because the 998×652 DEM was not transposed to match the 650×1000 mesh grid. The canonical scene matches the transposed DEM and has enabled convex-hull colliders on all seven placed rock meshes.
- WSL diagnostics see `cometbot_dev` with `/joy_node` and `/teleop_publisher` running, Stadia attached at BUSID 1-1, and `/dev/input/js0`/`event0`. The new image/container is available, but its teleop launch was not started to avoid duplicate control nodes.
- End-to-end Windows Isaac Sim DDS delivery, sensor output, powered motion, and sustained contact behavior remain unverified. Isaac Sim automatically migrated deprecated nodes in memory and showed an unsaved marker; no scene edits were saved to disk.

## Source status

- Original `Isaac-Sim`, `OmniLRS`, and `isaacsim-mcp-server` repositories with Git metadata are preserved in the adjacent source archive.
- Only simulation-relevant original scripts were retained under `legacy/archived_scripts/`; full CAN firmware/build output, general OmniLRS engine and lunar-yard assets, MCP/LLM services, unrelated scene experiments, and Jetbot assets are outside the project.
- Startup originals remain archived beside the implementation; the supported wrapper targets Docker inside WSL, unlike the Windows Docker Desktop context.

## Validation coverage

- **Passed:** nine Python tests (six ROS mapping, three terrain); canonical and local-Jackal Action Graph structural audits; terrain collider audit; 100% raw DEM height parity; candidate dependency scan (one Isaac-runtime shader unresolved); YAML/Compose parsing; PowerShell syntax checks; Humble image/package build.
- **Observed only:** WSL USB attachment, `/dev/input` devices, live legacy `/joy` and `/cmd_vel` nodes. This does not validate a nonzero joystick command reaching Isaac Sim.
- **Still required in Isaac Sim:** confirm sensor messages, test DDS delivery and nonzero teleop, and verify powered wheel motion plus terrain contact stability. The canonical scene is the launch target.
- **Terrain structural audit:** the canonical scene passes the read-only USD audit with 650,000 points, 1,296,702 triangles, one terrain collider, and seven of seven placed rock colliders. Isaac Sim visual review passed; dynamic rover contact is still pending.

See [source manifest](source-manifest.md), [known issues](known-issues.md), and [launch guide](setup/launch.md).
