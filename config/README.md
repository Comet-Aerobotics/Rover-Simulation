# Configuration and parity targets

These YAML files express project intent. Some values are loaded directly by ROS or terrain Python; others are checks against values authored in USD. Editing YAML alone does not necessarily change an open Isaac Sim stage.

| File | Main values | Runtime consumer / authority |
| --- | --- | --- |
| `terrain.yaml` | DEM paths, grid size/resolution, collision expectation, rut coefficients | `terrain/` and sand runtime read it; ground prim is still authored in USD |
| `joy.yaml` | Driver deadzone, repeat rate, device defaults | ROS Joy node(s); launch overrides `device_id` with selected WSL `/dev/input/jsN` IDs |
| `controller.yaml` | Axis indices, shaping, Twist rate, optional enable button | `teleop_publisher` reads it through `teleop.launch.py` |
| `ros.yaml` | Intended Humble/Fast DDS/domain 0 settings | Parity reference; actual container/Kit environment comes from Compose, `.env`, and launcher |
| `simulation.yaml` | Scene path, stage scale, robot joints/geometry, camera topics | Documentation/parity record; USD is authoritative for active prim values |

For example, `simulation.yaml` records a 55 kg rover estimate, but the canonical base-link USD authors `physics:mass = 0`; the explicit approximately 55 kg mass is in the separate working candidate. Likewise, two saved differential drive graphs have different wheel geometry. Verify the composed scene before using YAML as a physical measurement.

See [terrain variables](../docs/terrain.md), [rover parameters](../docs/rover.md), [ROS mapping](../docs/ros2.md), and [sensor outputs](../docs/sensors.md). Local installation paths and ROS domain overrides belong in `.env`, not in these shared YAML files.
