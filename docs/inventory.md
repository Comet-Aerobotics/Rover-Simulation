# Focused simulation inventory

**Updated:** 2026-11-04 | **Scope:** this LunaLab/Jackal simulation and its Stadia-to-ROS-to-Isaac control path.

The detailed responsibility-to-file audit is [ownership-and-migration.md](ownership-and-migration.md). Full initial repository intake and generated tooling/build outputs were moved outside the focused project to `../AIAA-Isaac-Sim-Rover-source-archive/`; no original source tree or user file was deleted. The active tree contains the selected local-Jackal scene dependency closure, relevant runtime code/configuration, preserved baseline and specifically relevant archived scripts. `work/` and ROS `build/`, `install/`, and `log/` are intentionally absent from the source tree; their preserved copies are in the adjacent archive.

## Authoritative system

| Component | Active source | Observed status |
|---|---|---|
| Stage | `scenes/CAMERASYNCSSMOETIMES_LOCAL_JACKAL_CANDIDATE.usd` (default); `scenes/CAMERASYNCSSMOETIMES.usd` (baseline) | Selected local-Jackal stage is Z-up, 1 m/unit, and was opened/rendered in Isaac Sim 6.1. The baseline remains unchanged; an older exact-name candidate stays archived because it has convex-hull terrain and active `Cube_003`. |
| Terrain | `assets/terrain/source/` (hash-verified copy of OmniLRS `Terrain_lidar01`), `config/terrain.yaml`, `terrain/` | Current stage has 650,000 vertices and 1,296,702 triangles; one static `PhysicsCollisionAPI` + `PhysicsMeshCollisionAPI` collider, approximation `none`, no terrain rigid body. Saved mesh heights match the cropped raw lidar01 DEM exactly; crater generation is optional and disabled by default. `Terrain_lidar02` is archived and not referenced by this scene. |
| Rover/graph | `/jackal` and `/jackal/ActionGraph` in selected local-Jackal scene; original baseline retained at `scenes/CAMERASYNCSSMOETIMES.usd` | Candidate opened and rendered in Isaac Sim 6.1, exposes four wheel DOFs, and produced a measured static wheel-terrain contact. Powered motion and contact stability remain open. |
| Camera | `/ActionGraph` in selected scene; imported enclosure at `assets/robots/camera/` | 640×400 depth render product; `/oak_d/depth`, active `oak_d/camera_info` helper, `oak_d_optical_frame`; output messages remain unverified. |
| ROS | `ros2/cometbot_ws/src/cometbot_control/` and `config/{joy,controller,ros}.yaml` | Humble package builds; live legacy nodes and Stadia device observed. Six mapping tests pass. |
| Docker | `docker/` | Humble image builds; new service is separate from active `cometbot_dev`, and DDS profile has no fixed initial peer. |

## Exact open dependencies/limitations

- Preserved baseline Jackal payload still references NVIDIA Isaac 5.0 `jackal.usd`; the selected VLP-16 scene uses the project copy and has matching graph joint names.
- The wall material's stale UI default was corrected to the existing normal map referenced by its MDL definition.
- The preserved baseline retains an anonymous Replicator sublayer, empty configuration payloads, and a remote Jackal reference. The selected local-Jackal scene omits these unusable composition arcs; it has been opened/rendered in Isaac Sim 6.1, though its graph node migration and full visual quality need review.
- Terrain generation reproduces raw lidar01 DEM heights exactly with craters disabled; cratered output is only an experiment.
- WSL diagnostics see `cometbot_dev` with `/joy_node` and `/teleop_publisher` running, Stadia attached at BUSID 1-1, and `/dev/input/js0`/`event0`. The new image/container is available, but its teleop launch was not started to avoid duplicate control nodes.
- End-to-end Windows Isaac Sim DDS delivery, sensor output, powered motion, and sustained contact behavior remain unverified. Isaac Sim automatically migrated deprecated nodes in memory and showed an unsaved marker; no scene edits were saved to disk.

## Source status

- Original `Isaac-Sim`, `OmniLRS`, and `isaacsim-mcp-server` repositories with Git metadata are preserved in the adjacent source archive.
- Only simulation-relevant original scripts were retained under `legacy/archived_scripts/`; full CAN firmware/build output, general OmniLRS engine and lunar-yard assets, MCP/LLM services, unrelated scene experiments, and Jetbot assets are outside the project.
- Startup originals remain archived beside the implementation; the supported wrapper targets Docker inside WSL, unlike the Windows Docker Desktop context.

## Validation coverage

- **Passed:** nine Python tests (six ROS mapping, three terrain); canonical and local-Jackal Action Graph structural audits; terrain collider audit; 100% raw DEM height parity; candidate dependency scan (one Isaac-runtime shader unresolved); YAML/Compose parsing; PowerShell syntax checks; Humble image/package build.
- **Observed only:** WSL USB attachment, `/dev/input` devices, live legacy `/joy` and `/cmd_vel` nodes. This does not validate a nonzero joystick command reaching Isaac Sim.
- **Still required in Isaac Sim:** confirm sensor messages/rendering, test DDS delivery and nonzero teleop, and verify powered wheel motion plus terrain contact stability. The local-Jackal scene is now the default launch target; the original USD is preserved unchanged as a baseline.
- **Terrain parity:** raw DEM height parity is exact; cratered output intentionally differs and is an experiment.

See [source manifest](source-manifest.md), [known issues](known-issues.md), and [launch guide](setup/launch.md).
