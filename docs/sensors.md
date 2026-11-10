# Cameras, lidar, and robot state outputs

Sensors are prims in the saved USD. Action Graph nodes create render products or read sensor/pose data and publish ROS 2 messages during playback. A visible camera or lidar model alone does not prove that a ROS topic is publishing useful data. The paths below were checked in the composed canonical and 55 kg scenes; topic delivery and image content depend on the running stage and bridge.

## OAK-style RGB and depth camera

| Item | Saved value or path | Use and limit |
| --- | --- | --- |
| Camera prim | `/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB` | Camera attached to the rover enclosure |
| Active camera graph | `/ActionGraph` | Creates a 640 × 400 render product and publishes RGB, depth, and camera info |
| RGB image | `/oak_d/rgb/image_raw` | `sensor_msgs/msg/Image`; inspect pixels and timestamps, not topic existence alone |
| Depth image | `/oak_d/depth` | `sensor_msgs/msg/Image`; inspect encoding, units, and invalid pixels in the consumer |
| Camera info | `/oak_d/rgb/camera_info` and `/oak_d/camera_info` | Separate graph nodes; compare intrinsics and frame IDs with the chosen image stream |
| Frame ID | `oak_d_optical_frame` | Authored on camera publisher nodes; verify it connects to the robot TF tree |
| Clipping range | 0.05–1000 m | Geometry outside the range does not render into this camera |
| Authored lens values | Focal length about 23.9075; horizontal aperture 19.2; vertical aperture 12.0 | USD camera parameters, not a physical calibration certificate |

The stage also contains two infrared camera prims under `camera_link`, a `third_person` camera, three fixed `/World/Cameras/*` views, and a second 640 × 480 render product aimed at the OAK RGB camera. Their presence does not mean they publish the current RGB/depth topics. The active 640 × 400 graph is the path to inspect first. Its OAK camera sensor is configured for 10 Hz. A legacy camera-info helper is disabled. Neither the precise physical mount nor camera-info calibration has been checked against hardware.

The OAK prim has no authored `omni:sensor:tickRate` in the inspected stage. A headless 10 Hz tick-rate trial improved frame time while still delivering RGB/depth, but the required application rate is not established and that setting was not saved. See [performance analysis](performance-analysis.md).

## VLP-16 lidar and visualization

| Item | Saved value or path | Use and limit |
| --- | --- | --- |
| Lidar prim | `/jackal/base_link/laser/Lidar` | Enabled PhysX lidar on the rover |
| Publish graph | `/jackal/ROS2_Graph/LiDARGraph` | Reads lidar beams and publishes `sensor_msgs/msg/LaserScan` on `/scan` |
| Horizontal field of view / resolution | 360° / about 0.4° | Saved sensor configuration |
| Vertical field of view / resolution | 40° / about 2.7° | Saved sensor configuration; `/scan` is still a 2D ROS message |
| Viewport display | `drawLines = true`, `drawPoints = true` | Controls visible rays/hits; separate from `/scan` delivery |

The shared Jackal lidar USD was edited to enable ray and point drawing. Reload the stage after saving unrelated edits to see those asset settings. An actual `/scan` message reached WSL; the current viewport appearance still needs direct GUI acceptance. This repository does not document an active lidar point-cloud publisher.

## TF, odometry, and simulation clock

| Graph | Data path | Check |
| --- | --- | --- |
| `/jackal/ROS2_Graph/TFGraph` | Robot pose/odometry → ROS transforms and odometry | Observe `/tf` and inspect frame names and continuity |
| `/jackal/ROS2_Graph/ClockGraph` | Simulation time → ROS clock | Verify `/clock` advances only during Play |
| `/ROS2_Connection_Test` | Additional clock publication graph | Inspect before changing duplicate time publishers |

A sampled `/tf` message contained laser and camera frames despite earlier PoseTree warnings. That sample does not prove every transform is correct over a drive. Camera and lidar graphs also depend on the ROS 2 Bridge, matching domain/middleware, and a playing timeline.

## Practical acceptance sequence

1. Start the intended scene, press **Play**, and confirm the ROS 2 Bridge loaded. Record the exact scene and domain.
2. In the ROS container, inspect `ros2 topic info /oak_d/rgb/image_raw`, `/oak_d/depth`, `/scan`, `/tf`, and `/clock`. A topic with a publisher is only a wiring check.
3. Receive a real image and scan. Check image dimensions/content, depth encoding, scan range array, timestamps, and frame IDs. Compare the camera image against a visible landmark.
4. Move the rover gently. Confirm the camera view and laser/TF frames change with it, and compare the viewport ray/point overlay with `/scan` separately.
5. If frames stop during sand updates, verify that the scene was built with visible collision tiles and the runtime printed `AIAA_SAND_READY`; see [terrain](terrain.md).

For graph ownership and helper node names, use [Action Graphs](isaac/action-graph.md). For current acceptance limits, use [known issues](known-issues.md).
