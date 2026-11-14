# Cameras, lidar, and robot state outputs

Sensors are prims in the saved USD. Action Graph nodes create render products or read sensor/pose data and publish ROS 2 messages during playback. A visible camera or lidar model alone does not prove that a ROS topic is publishing useful data. The paths below were checked in the composed canonical and 55 kg scenes; topic delivery and image content depend on the running stage and bridge.

## OAK-style RGB and depth camera

**OAK** is Luxonis's OpenCV AI Kit camera family. An actual OAK-D Pro combines a color camera with two monochrome stereo cameras; its processor matches left/right image features to estimate depth. The Pro infrared dot projector adds texture to plain surfaces such as a floor, and its IR flood illumination helps in low light. OAK hardware can also run vision models on-device through DepthAI and report motion from an integrated IMU. Those hardware capabilities are described in the [Luxonis overview](https://docs.luxonis.com/overview), [depth guide](https://docs.luxonis.com/hardware/platform/features/depth), and [OAK-D Pro comparison](https://docs.luxonis.com/hardware/platform/comparison/vs-realsense).

On a rover, RGB can support visual inspection, object detection, and terrain classification. Depth gives a range for many image pixels, enabling obstacle geometry, local 3D mapping, and checks on a path ahead; RGB plus depth can assign color to 3D points. CameraInfo carries the projection parameters needed to turn image pixels into rays, and TF places those rays relative to the rover. These are potential consumers of the streams, not autonomous behaviors supplied by the current graph. The VLP-16 lidar is a separate range sensor with a `/scan` publisher and viewport ray/point display. Controller commands and wheel response do not require the OAK image streams.

| Item | Saved value or path | Use and limit |
| --- | --- | --- |
| Camera prim | `/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB` | Camera attached to the rover enclosure |
| Active camera graph | `/ActionGraph` in canonical/sand; `/CameraActionGraph` in the modified 55 kg rigid candidate | Creates a 640 × 400 render product and publishes RGB, depth, and camera info |
| RGB image | `/oak_d/rgb/image_raw` | `sensor_msgs/msg/Image`; inspect pixels and timestamps, not topic existence alone |
| Depth image | `/oak_d/depth` | `sensor_msgs/msg/Image`; inspect encoding, units, and invalid pixels in the consumer |
| Camera info | `/oak_d/rgb/camera_info` and `/oak_d/camera_info` | Separate graph nodes; compare intrinsics and frame IDs with the chosen image stream |
| Frame ID | `oak_d_optical_frame` | Authored on camera publisher nodes; verify it connects to the robot TF tree |
| Clipping range | 0.05–1000 m | Geometry outside the range does not render into this camera |
| Authored lens values | Focal length about 23.9075; horizontal aperture 19.2; vertical aperture 12.0 | USD camera parameters, not a physical calibration certificate |

The stage also contains two infrared camera prims under `camera_link`, a `third_person` camera, three fixed `/World/Cameras/*` views, and a second 640 × 480 render product aimed at the OAK RGB camera. Their presence does not mean they publish the current RGB/depth topics. The active 640 × 400 graph is the path to inspect first. A legacy camera-info helper is disabled. The modified 55 kg rigid candidate's camera prim is 5.389 m from its named enclosure and fails the forward-axis check; that camera pose needs review before using its imagery for rover-mounted perception. Camera-info calibration has not been checked against hardware.

This simulation currently models an OAK-like **output interface**, not the OAK-D Pro's complete sensing process. The active graph renders one rover-mounted camera viewpoint and derives RGB and depth images from Isaac Sim's scene renderer; it does not stereo-match the two infrared prims, project IR dots, model low-texture depth failures, emulate the onboard DepthAI processor, or publish an OAK IMU stream. Rendered depth is therefore an idealized geometry measurement, not a validated prediction of real OAK stereo accuracy on sand. The camera model and CameraInfo still require content and calibration acceptance before using them for physical sensor validation.

The launcher sets the OAK prim's `omni:sensor:tickRate` to 10 Hz in memory unless `ROVER_OAK_TICK_RATE_HZ` selects another rate; some saved scenes have no authored rate. A drained ROS probe counted 36 RGB and 36 depth messages over four simulated seconds at 10 Hz, versus six of each at 2 Hz. For fast controller use, `-NoOak` disables the active OAK graph before Play, including `/CameraActionGraph` in the modified 55 kg rigid candidate; image and camera-info streams then stop, while lidar, TF, clock, and driving remain. Fresh full-GUI camera-off runs measured 58.0–61.7 FPS while idle and 56.0 FPS while driving, versus roughly 40–45 with OAK enabled. A matched Tracy trace found that much of this gap is a timeline scheduling change: camera-on fast mode executes roughly three times as many physics updates per displayed frame. With the timeline mode matched, OAK adds about 1.1–2.3 ms/frame. See [performance analysis](performance-analysis.md).

## VLP-16 lidar and visualization

| Item | Saved value or path | Use and limit |
| --- | --- | --- |
| Lidar prim | `/jackal/base_link/laser/Lidar` | Enabled PhysX lidar on the rover |
| Publish graph | `/jackal/ROS2_Graph/LiDARGraph` | Reads lidar beams and publishes `sensor_msgs/msg/LaserScan` on `/scan` |
| Horizontal field of view / resolution | 360° / about 0.4° | Saved sensor configuration |
| Vertical field of view / resolution | 40° / about 2.7° | Saved sensor configuration; `/scan` is still a 2D ROS message |
| Rotation rate | 10 Hz | Shared asset setting; a full 900-range scan was received with `scan_time = 0.1 s` |
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
