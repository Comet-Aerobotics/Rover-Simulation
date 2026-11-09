# Isaac Sim integration

The USD stage owns the live robot, environment, sensor prims, and Action Graphs. This folder contains inspection, launch-hook, and sand-runtime code; it is not a second scene definition.

| Path | Role |
| --- | --- |
| `diagnostics/open_scene_on_start.py` | Opens the launcher-selected USD inside Kit and attaches sand runtime when requested |
| `diagnostics/validate_action_graph.py` | Read-only saved graph audit |
| `diagnostics/inspect_stage.py`, `runtime_acceptance.py` | Stage inventory and controlled runtime checks |
| `diagnostics/set_rover_mass.py` | Opt-in scene mass edit helper; inspect target before using |
| `diagnostics/prepare_local_jackal_scene.py` | Writes a separate candidate with local Jackal references |
| `terrain/sand_runtime.py` | Samples wheel motion/contact and rebuilds touched visible collision tiles during Play |

Read-only USD scripts need Python with `pxr` bindings (`py -m pip install -e ".[usd-audit]"`); live helpers need Isaac Sim's Python and an active stage. Scene-editing helpers should target separate candidate files. The selected stage has seven OmniGraph hierarchies: two drive paths, one OAK camera graph, lidar, TF, clock, and a connection-test clock graph. See [Action Graphs](../docs/isaac/action-graph.md), [rover](../docs/rover.md), [sensors](../docs/sensors.md), and [launch](../docs/setup/launch.md) before editing any of them.
