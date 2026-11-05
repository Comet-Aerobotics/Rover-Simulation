# ROS 2 control path

`joy_node` publishes `/joy` (`sensor_msgs/msg/Joy`). `cometbot_control/teleop_publisher` subscribes to `/joy`, applies axis selection (linear 1, angular 3), 0.1 deadzone, cubic shaping, then publishes `/cmd_vel` (`geometry_msgs/msg/Twist`) at 20 Hz. The optional enable button defaults off (`-1`); configure a real deadman button before enabling. Missing axes publish zero. The graph subscribes to `/cmd_vel` in Isaac Sim.

Observed runtime: Docker Humble/Fast DDS/domain 0 had `/joy`, `/cmd_vel`, `/joy_node`, `/teleop_publisher`; a sampled idle Joy and Twist were zero. This verifies graph entities are present, not that the Xbox/Stadia input changes values or that Windows Isaac receives commands. That end-to-end test is unresolved.

Windows Isaac Sim bundle defaults to Jazzy and Zenoh in this installation; select `rmw_fastrtps_cpp` and align `ROS_DOMAIN_ID=0`. Docker is Humble/Fast DDS. Mixed ROS distributions can interoperate at DDS level but must be validated. Clear stale `FASTRTPS_DEFAULT_PROFILES_FILE`/`FASTDDS_DEFAULT_PROFILES_FILE` overrides unless they point to this repo's reviewed profile. The old `10.255.255.254` initial peer is intentionally omitted.

Read-only health: `ros2 node list`, `ros2 topic info /joy`, `ros2 topic info /cmd_vel`, and `ros2 topic echo --once /joy` / `--once /cmd_vel`. Use an isolated ROS domain for mapping tests. Do not send nonzero commands on the active domain without the rover safely immobilized. End-to-end validation requires a nonzero controlled Joy input, observed Twist, Isaac subscriber match, and measurable wheel response; report each separately.
