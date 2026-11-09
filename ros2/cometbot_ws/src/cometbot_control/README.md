# `cometbot_control` package

| Path | Job |
| --- | --- |
| `cometbot_control/mapping.py` | Clips Joy axes, applies radial deadzone and signed cubic shaping; missing axes return zero |
| `cometbot_control/teleop_publisher.py` | Reads YAML parameters, subscribes to `/joy`, publishes `/cmd_vel` at 20 Hz; Joy older than 0.5 s yields zero |
| `launch/teleop.launch.py` | Starts one Joy node or a split left/right pair and `teleop_publisher`; layout/IDs come from `ROVER_JOY_LAYOUT` and `ROVER_JOY_DEVICE_IDS` |
| `test/test_mapping.py` | Mapping behavior tests independent of ROS runtime |
| `setup.py`, `package.xml` | Humble package entry point and dependencies |

The current project settings are in `config/joy.yaml` and `config/controller.yaml` at the repository root. In the single-controller default, axis 1 controls linear motion and axis 3 turning. The optional paired launch uses left axis 1 and right axis 0. The 0.1 teleop deadzone and cubic power shape the command. See [ROS 2 guide](../../../../docs/ros2.md) for the full parameter and topic table.

Docker mounts the parent colcon workspace at `/workspace` and builds this package there. `build/`, `install/`, and `log/` are generated workspace outputs, not package source.
