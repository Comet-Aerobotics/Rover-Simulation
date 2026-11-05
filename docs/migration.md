# Focused migration record

The active project is limited to the LunaLab rover scene and its control/sensor path. Broad source intake was retained but moved to the adjacent `AIAA-Isaac-Sim-Rover-source-archive/` so the project tree is not a mirror of entire unrelated repositories.

## Kept active

- Original terrain-test-derived baseline `scenes/CAMERASYNCSSMOETIMES.usd`, preserved with local layer paths and inactive `Cube_003`.
- `scenes/CAMERASYNCSSMOETIMES_LOCAL_JACKAL_CANDIDATE.usd`, the selected local-Jackal scene. It opened/rendered in Isaac Sim 6.1 and static wheel-terrain contact was measured. The original baseline remains unchanged.
- Referenced LunaLab layers/textures, configuration USDs, the OAK enclosure, terrain source rasters, and two local Jackal candidates.
- ROS 2 Humble teleop package, observed Joy/teleop parameters, reviewed Fast DDS profile, WSL/Docker startup/health scripts, and the terrain/Action Graph auditors.
- `scripts/windows/start_rover.ps1` is the supported combined entry point; `start_rover_all.ps1` is a compatibility alias; `start_isaac_sim.ps1` launches Isaac Sim alone. AI/MCP behavior from the original `start_stack_fixed.ps1` remains excluded.

## Retained as selected legacy references

`legacy/archived_scripts/` holds the original OmniLRS Lunalab terrain loader and DEM preprocessor; camera/Action Graph setup drafts; the separate Isaac terrain-crater experiment; original `start_rover_all.ps1` and `start_stack_fixed.ps1`; and the original broad microros Compose/DDS files. They inform migration but are not run as current entry points.

## Kept outside active project

- Full OmniLRS source tree, general lunar-yard/terrain engine and unrelated assets.
- MCP server, local model launch, and AI services.
- CAN/micro-ROS firmware and workspace build output.
- Unvalidated scene alternatives, including ROVERFALLS and Jetbot experiments.

Everything above remains in the adjacent source archive with Git metadata and intake manifests. The original user folders remain intact.

## Migration/rollback state

Source-copy and asset relocation are complete. ROS image/package and headless tests passed. The saved USD terrain and graph audits pass structurally; raw DEM regeneration matches saved heights exactly. The local-Jackal scene and wall-material metadata correction remove project-owned unresolved assets, leaving only the Isaac-runtime `OmniPBR.mdl` dependency in the standalone audit. Static wheel-terrain contact and rendering are observed in Isaac Sim 6.1; powered motion, sustained contact stability, sensor output, Windows↔WSL DDS delivery, and nonzero Joy input remain pending. The legacy container remains live and untouched. The new container image/package was built; its container is available without launching teleop. Use `docs/setup/launch.md` for a guarded teleop transition after legacy nodes are stopped.
