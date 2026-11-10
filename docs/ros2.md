# ROS 2 control and data flow

ROS 2 Humble runs in `aiaa_rover_dev` under WSL/Docker. Isaac Sim runs on Windows with its ROS 2 Bridge. Both sides use Fast DDS (`rmw_fastrtps_cpp`) and normally domain 0. The container has host networking in WSL and bind-mounts `/dev/input`; a Windows USB controller must also appear as `/dev/input/jsN` in WSL and be readable in the container. The launcher passes selected numeric device IDs to the Joy launch. The current working tree also supports an optional two-device layout for a split controller; the previously confirmed drive used a single controller.

```text
controller → joy_node → /joy → teleop_publisher → /cmd_vel
                                             ↓ Fast DDS / ROS 2 Bridge
                                 Isaac drive graph → wheel articulation
Isaac camera/lidar/pose/clock graphs → image, depth, scan, TF, odometry, clock
```

## Topic and owner map

| Topic | Type | Publisher → consumer | What to verify |
| --- | --- | --- | --- |
| `/joy` | `sensor_msgs/msg/Joy` | Docker `joy_node` → `teleop_publisher` | Axis values change with the selected controller |
| `/joy_left`, `/joy_right` | `sensor_msgs/msg/Joy` | Optional paired Joy nodes → `teleop_publisher` | Both devices must be fresh; left axis 1 requests linear motion and right axis 0 requests turning in the current launch code |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | `teleop_publisher` → Isaac drive graph(s) | Nonzero `linear.x`/`angular.z`, Isaac subscriber, wheel response |
| `/oak_d/rgb/image_raw` | `sensor_msgs/msg/Image` | Isaac OAK graph → ROS consumers | Frame content, 640 × 400 target, timestamps |
| `/oak_d/depth` | `sensor_msgs/msg/Image` | Isaac OAK graph → ROS consumers | Encoding, depth units, usable pixels |
| `/oak_d/rgb/camera_info`, `/oak_d/camera_info` | `sensor_msgs/msg/CameraInfo` | Isaac camera-info helpers | Frame ID and calibration match corresponding stream |
| `/scan` | `sensor_msgs/msg/LaserScan` | Isaac lidar graph | Range data and frame ID, independent of viewport ray display |
| `/tf` | `tf2_msgs/msg/TFMessage` | Isaac transform graph | Camera/laser/base frame connectivity while driving |
| `/clock` | `rosgraph_msgs/msg/Clock` | Isaac clock graph(s) | Advances during Play; inspect duplicate publishers if unexpected |

The TF graph contains an odometry publisher, but its exact topic and frame semantics should be read from the running graph before building downstream navigation around it. Topic names alone cannot prove message content or synchronized timing. See [sensors](sensors.md) and [Action Graphs](isaac/action-graph.md).

To turn the OAK depth stream into a point cloud, install `depth_image_proc`, build `cometbot_control`, and run `ros2 launch cometbot_control pointcloud.launch.py` in a ROS-sourced Humble shell. The launch file binds `image_rect` to `/oak_d/depth`, binds the derived `/camera_info` subscription to `/oak_d/camera_info`, and publishes `/oak_d/points`. From the repository root, run `python3 scripts/linux/check_camera_sync.py` to measure actual depth, CameraInfo, and exact timestamp pairs. Set `--min-depth-hz` to the wall-clock rate required by your application; the default is 1 Hz to detect a stalled stream while the simulation runs slower than real time.

## Joystick-to-Twist mapping

`ros2/cometbot_ws/src/cometbot_control/cometbot_control/teleop_publisher.py` normally subscribes to `/joy` and publishes `/cmd_vel` every 1/20 s. In the optional paired layout it subscribes to `/joy_left` and `/joy_right`, using one device for linear and the other for angular input. `mapping.py` clips selected axes to [-1, 1], applies a radial deadzone, then preserves sign while cubing each value. Single-source input older than 0.5 s produces zero; in paired mode both sources must be fresh. Missing axes also produce zero. The configured enable-button index is `-1`, meaning the optional button gate is disabled; set a real deadman index only after verifying the controller's button ordering.

| Setting | Current value | File / effect |
| --- | ---: | --- |
| `linear_axis` | 1 | `config/controller.yaml`; forward/back command in single layout and left device in paired layout |
| `angular_axis` | 3 single; 0 paired | `config/controller.yaml` single default; paired launch overrides to right-device axis 0 |
| `deadzone` | 0.1 | `config/controller.yaml`; suppresses small combined stick movement |
| `joystick_power` | 3 | `config/controller.yaml`; finer control near center |
| `cmd_vel_pub_frequency` | 20 Hz | `config/controller.yaml`; repeated Twist output |
| `enable_button_index` | -1 | `config/controller.yaml`; no button gate currently |
| `joy_node.deadzone` | 0.05 | `config/joy.yaml`; driver-side stick filtering before mapping |
| `joy_node.autorepeat_rate` | 20 Hz | `config/joy.yaml`; repeated Joy samples |
| `ROS_DOMAIN_ID` | 0 by default | `.env`, `config/ros.yaml`, Compose and Isaac launcher must agree |
| Middleware | `rmw_fastrtps_cpp` | Docker and Isaac startup select Fast DDS |

The mapping output is a requested velocity pair; actual rover speed depends on the saved graph, wheel contact, physics, and terrain. The additional saved drive graph has different wheel geometry, so do not infer physical speed from the normalized joystick value without a drive test.

## Runtime ownership and commands

| Component | Source | Runtime behavior |
| --- | --- | --- |
| ROS image and workspace | `docker/Dockerfile`, `docker/compose.yaml`, `ros2/cometbot_ws` | Builds Humble package in `/workspace`, starts `aiaa_rover_dev` |
| Teleop launch | `ros2/cometbot_ws/src/cometbot_control/launch/teleop.launch.py` | Starts one Joy node or optional left/right Joy nodes, plus `teleop_publisher` |
| Host orchestration | `scripts/windows/start_rover.ps1` | Checks USB/WSL, chooses joystick, starts or reuses container and nodes |
| Isaac ROS environment | `scripts/windows/start_isaac_sim.ps1` | Selects bundled Humble, Fast DDS, ROS domain, and intended scene before Kit starts |
| Legacy container | `cometbot_dev` | Separate prior work; launcher checks for duplicate Joy/teleop processes |

In the repository root, run `.\scripts\windows\start_rover_all.ps1 -Mode Diagnostics` before Start. For a live check from a shell inside the ROS container:

```bash
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
ros2 node list
ros2 topic info /joy
ros2 topic info /cmd_vel
ros2 topic echo --once /joy
ros2 topic echo --once /cmd_vel
```

Run the `echo` commands while Isaac is playing and the controller is safely operated. A successful user test already established single-controller motion in the open 55 kg candidate and sensors reached WSL in that session. The new paired-controller path has not yet had the same end-to-end check. A later launcher run showed zero Isaac `/cmd_vel` subscribers while an existing Kit process retained its prior environment. Treat each launch as a new check: an already-running Kit process will not inherit a new ROS domain or middleware setting. Do not change firewall or DDS peers solely because a topic name exists. The reviewed Fast DDS profile deliberately has no fixed `10.255.255.254` peer.

## If a link fails

| Symptom | First check |
| --- | --- |
| No `/dev/input/jsN` | `usbipd list` on Windows; device attachment and Linux HID support in WSL |
| Joystick visible in WSL, not container | `/dev/input` mount, character-device permission, input group; rerun launcher after attachment |
| `/joy` stays zero | Selected joystick ID, Joy axis numbering, physical controller input |
| `/joy` moves, `/cmd_vel` stays zero | Mapping axis indices, deadzone, freshness timeout, optional button gate |
| `/cmd_vel` has no Isaac subscriber | Press Play; check ROS Bridge, matching domain/middleware, Kit process environment |
| Subscriber exists but rover does not move | Inspect both saved drive graphs, articulation target, wheel joints, physics contact |
| Images/scans/TF absent | Inspect the matching USD graph and sensor prim; see [sensors](sensors.md) |

`ros2 topic info` and message sampling are read-only checks. Coordinate any deliberate nonzero command with the operator when the rover is in a safe scene. The [mapping tests](../ros2/cometbot_ws/src/cometbot_control/test/test_mapping.py) cover pure axis/deadzone behavior; they do not test the Windows-to-Isaac network or wheel contact.
