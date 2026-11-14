# USD Action Graphs

The selected USD owns its OmniGraph nodes. They evaluate during simulation playback, so a paused stage can contain correct-looking wiring without publishing data or moving the rover. `isaac/diagnostics/validate_action_graph.py` checks saved structure; actual output requires a runtime check.

## Graph inventory

| Graph path | Main nodes / job | Output or risk |
| --- | --- | --- |
| `/jackal/ActionGraph` | ROS2SubscribeTwist → stage-unit conversion → DifferentialController → articulation controllers | Intended `/cmd_vel` to wheel command path |
| `/jackal/ROS2_Graph/DriveGraph` | Imported Jackal's standalone drive path | Active in the reusable asset; deactivated by the rover scene's USD layer so it does not evaluate in the composed simulation |
| `/ActionGraph` or `/CameraActionGraph` | CreateRenderProduct, depth/RGB camera helpers, camera-info helpers | OAK ROS image, depth, and camera-info streams; the modified 55 kg rigid candidate uses the latter path |
| `/jackal/ROS2_Graph/LiDARGraph` | Read PhysX lidar beams → ROS2PublishLaserScan | `/scan` |
| `/jackal/ROS2_Graph/TFGraph` | Read pose/odometry → transform/odometry publishers | TF and odometry outputs |
| `/jackal/ROS2_Graph/ClockGraph` | Read simulation time → ROS2PublishClock | `/clock` |
| `/ROS2_Connection_Test` | Playback tick, time, clock publication | Additional saved clock path; inspect before removing |

The camera graph is at the stage root (`/ActionGraph` in canonical/sand, `/CameraActionGraph` in the modified 55 kg rigid candidate); rover drive and pose/lidar graphs are under `/jackal`. The scene's inactive override on the imported drive graph applies even when the USD is opened manually. The launch hook checks that no second drive graph is active, configures OAK rate or fast teleop mode, and attaches sand runtime when requested. Manually opening the saved USD bypasses those in-memory sensor and sand settings.

## Drive graph ownership

The imported asset's standalone graph uses a 0.09 m wheel radius and 0.335 m wheel distance. The scene controller uses 0.098 m and 0.3755 m, plus a stage-unit conversion. Both graphs previously subscribed to Twist and sent commands to the same articulation. The rover scenes now author `active = false` on the imported graph, while the asset keeps it for standalone use. In a prior controlled straight command, deactivating the duplicate changed travel from about 0.93 m to 1.28 m over three simulated seconds. Normal launcher runs already applied this deactivation in memory, so saving it in the scene primarily fixes direct USD opens and removes the launch-time mutation; it is not expected to add another large FPS gain.

The intended graph sends four wheel tokens: `front_left_wheel`, `front_right_wheel`, `rear_left_wheel`, and `rear_right_wheel`. These match the four composed revolute joints under `/jackal/base_link/`. Its saved max acceleration, angular acceleration, angular speed, deceleration, linear speed, and wheel speed inputs are approximately 29.0, 55.0, 29.6, 87.3, 97.7, and 202.5 respectively. Their effective physical limits have not been independently calibrated.

## Camera and lidar graph checks

The OAK camera prim is `/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB`. The active camera graph's `CreateRP` node targets 640 × 400. The launcher sets its `OmniSensorAPI` tick rate to 10 Hz unless configured otherwise. Its OpenCV pinhole model supplies the 640 × 400 image size and all required coefficients; missing fields cause Isaac Sim 6.1's CameraInfo helper to fail. Depth helper `CamHelper` publishes `/oak_d/depth`; `RGBHelper` publishes `/oak_d/rgb/image_raw`; `RGBInfoHelper` publishes `/oak_d/rgb/camera_info`. The depth camera-info helper publishes `/oak_d/camera_info`. A legacy `CamHelperInfo` is disabled. The publisher frame ID is `oak_d_optical_frame`. Full-GUI ablations measured 40–45 FPS with an image writer active versus 58–62 FPS with the camera graph off, but a matched Tracy trace showed that much of that difference is the camera-on condition's faster timeline scheduling; the remaining camera-on cost was about 1.1–2.3 ms/frame. `-NoOak` is available for controller sessions. Confirm the resolved topic names, image content, and header timestamps in ROS rather than relying on node labels.

The lidar graph reads `/jackal/base_link/laser/Lidar` beams and publishes a LaserScan. The lidar asset's `drawLines` and `drawPoints` settings control the viewport overlay and do not gate ROS scan publication. The TF graph can publish the sensor frames even when PoseTree logs warnings; verify actual `/tf` messages and frame connectivity.

## How to inspect safely

```powershell
py -m pip install -e ".[usd-audit]"
py isaac/diagnostics/validate_action_graph.py --local-jackal scenes/CAMERASYNCSSMOETIMES.usd
py isaac/diagnostics/validate_action_graph.py --local-jackal --drive-only 'scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd'
```

The script needs Python with `pxr` USD bindings; the [Isaac integration index](../../isaac/README.md) lists other helpers. In Isaac Sim, open the intended graph, press Play, and check one link at a time: received Twist, differential output, articulation wheel commands, and actual base movement. For sensors, check render product, publisher node, message payload, and timestamp. Isaac Sim 6.1 can migrate old node types in memory and mark a stage unsaved; review the resulting diff before saving the canonical scene.
