# Source and preservation manifest

**Updated:** 2026-11-02 | **Full archive:** `../AIAA-Isaac-Sim-Rover-source-archive/` (sibling to this focused project). Original user source paths were not modified or deleted.

| Original source | Preserved location | Intake count/size | Focused-project disposition |
|---|---|---:|---|
| `Documents/Aerobotics/Isaac-Sim` | `../AIAA-Isaac-Sim-Rover-source-archive/source_snapshots/Isaac-Sim` | 1,296 regular files / 68,825,680 bytes | Selected ROS teleop, launchers, graph drafts and terrain experiment preserved under `legacy/archived_scripts/`; full repo and CAN/build artifacts are external archive. |
| `Documents/Aerobotics/isaacsim-mcp-server` | `../AIAA-Isaac-Sim-Rover-source-archive/source_snapshots/isaacsim-mcp-server` | 3,875 / 114,358,397 bytes | Optional MCP integration, outside this simulation. |
| `Documents/OmniLRS` | `../AIAA-Isaac-Sim-Rover-source-archive/source_snapshots/OmniLRS` | 2,240 / 7,872,404,048 bytes | Only scene dependency closure, two Jackal model candidates, license, DEM inputs, and relevant loader/preprocessor were promoted. Generic lunar-yard worlds, OmniLRS engine code and unrelated assets remain archived. |
| Windows startup scripts | `../AIAA-Isaac-Sim-Rover-source-archive/source_snapshots/launchers/` and `legacy/archived_scripts/*original.ps1` | 3 launchers | New supported entry point is `scripts/windows/start_rover.ps1`; old behavior remains available for comparison. |
| Historical `fastdds.xml`, original Compose/Dockerfile | `../AIAA-Isaac-Sim-Rover-source-archive/source_snapshots/...` and `legacy/archived_scripts/microros-*original.*` | — | Preserved; old config includes problematic peer/physical CAN and broad privileges, not used as simulation default. |
| 13 original Documents/Desktop USD candidates | `../AIAA-Isaac-Sim-Rover-source-archive/source_snapshots/scenes/` | 13 | One terrain-test-derived stage is canonical. Unvalidated copies moved from `scenes/test_scenes/` to `../AIAA-Isaac-Sim-Rover-source-archive/candidate_scenes/`. |

## Preservation notes

- The full source snapshots were moved intact from the focused workspace into the adjacent named archive; no source files were removed. The copies retain Git metadata and local worktree state.
- Two WSL-generated `latest_build` reparse-point directories inside the Isaac-Sim CAN tree were empty/unreproducible in the initial Windows copy; the original user directories remain unchanged.
- Assets actively referenced by the selected USD were copied into this project and their local paths redirected only in the new USD copy. The original source scenes remain archived.
- The local wall-layer Black Matte UI default was corrected to the map already used by its active input and MDL definition; the preserved OmniLRS source copy is unchanged. The local-Jackal candidate scene is reproducibly generated from the canonical project copy by `isaac/diagnostics/prepare_local_jackal_scene.py`.
- The active `scenes/test_scenes/` folder intentionally has no unvalidated scenes. Scene candidates live outside the focused project until explicitly selected for a test.
