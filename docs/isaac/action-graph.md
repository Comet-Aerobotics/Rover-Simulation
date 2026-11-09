# USD Action Graphs

The selected USD owns its OmniGraph nodes. They evaluate during simulation playback, so a paused stage can contain correct-looking wiring without publishing data or moving the rover. `isaac/diagnostics/validate_action_graph.py` checks saved structure; actual output requires a runtime check.

## Graph inventory

| Graph path | Main nodes / job | Output or risk |
| --- | --- | --- |
| `/jackal/ActionGraph` | ROS2SubscribeTwist → stage-unit conversion → DifferentialController → articulation controllers | Intended `/cmd_vel` to wheel command path |
| `/jackal/ROS2_Graph/DriveGraph` | Second ROS2SubscribeTwist and differential/articulation path | Also active; has different wheel radius/distance and can compete with intended drive path |
| `/ActionGraph` | CreateRenderProduct, depth/RGB camera helpers, camera-info helpers | OAK ROS image, depth, and camera-info streams |
| `/jackal/ROS2_Graph/LiDARGraph` | Read PhysX lidar beams → ROS2PublishLaserScan | `/scan` |
| `/jackal/ROS2_Graph/TFGraph` | Read pose/odometry → transform/odometry publishers | TF and odometry outputs |
| `/jackal/ROS2_Graph/ClockGraph` | Read simulation time → ROS2PublishClock | `/clock` |
| `/ROS2_Connection_Test` | Playback tick, time, clock publication | Additional saved clock path; inspect before removing |

The stage inventory found seven OmniGraph prims and 59 graph nodes in the 55 kg candidate. The camera graph is at the stage root; rover drive and pose/lidar graphs are under `/jackal`. Graph ownership is independent of the Python launch hook, which only opens the scene and attaches sand runtime when requested.

## Drive parameters that require parity

| Parameter | `/jackal/ActionGraph` | `/jackal/ROS2_Graph/DriveGraph` | Implication |
| --- | ---: | ---: | --- |
| Wheel radius | 0.098 m | 0.09 m | Different wheel speed for the same linear request |
| Wheel distance | 0.3755 m | 0.335 m | Different left/right speeds for the same turn request |
| Max linear speed input | About 97.7 stage-authored units | 0.3 | Limits are not directly comparable without checking unit conversion and active path |
| ROS Twist subscriber | `/cmd_vel` explicit | Topic input not explicitly authored in the inspected node | Both subscribed to Twist in prior runtime inspection |

The intended graph sends four wheel tokens: `front_left_wheel`, `front_right_wheel`, `rear_left_wheel`, and `rear_right_wheel`. These match the four composed revolute joints under `/jackal/base_link/`. Its saved max acceleration, angular acceleration, angular speed, deceleration, linear speed, and wheel speed inputs are approximately 29.0, 55.0, 29.6, 87.3, 97.7, and 202.5 respectively. Their effective physical limits have not been independently calibrated. The user observed normal controller-driven motion in the 55 kg candidate, so duplicate-graph cleanup should begin with a controlled A/B drive rather than an untested deletion.

## Camera and lidar graph checks

The OAK camera prim is `/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB`. `/ActionGraph/CreateRP` targets 640 × 400. Depth helper `CamHelper` publishes `/oak_d/depth`; `RGBHelper` publishes `/oak_d/rgb/image_raw`; `RGBInfoHelper` publishes `/oak_d/rgb/camera_info`. The separate camera-info helper uses `oak_d/camera_info` without a leading slash in its authored input. A legacy `CamHelperInfo` is disabled. The publisher frame ID is `oak_d_optical_frame`. Confirm the resolved topic names and image content in ROS rather than relying on node labels.

The lidar graph reads `/jackal/base_link/laser/Lidar` beams and publishes a LaserScan. The lidar asset's `drawLines` and `drawPoints` settings control the viewport overlay and do not gate ROS scan publication. The TF graph can publish the sensor frames even when PoseTree logs warnings; verify actual `/tf` messages and frame connectivity.

## How to inspect safely

```powershell
py -m pip install -e ".[usd-audit]"
py isaac/diagnostics/validate_action_graph.py --local-jackal scenes/CAMERASYNCSSMOETIMES.usd
```

The script needs Python with `pxr` USD bindings; the [Isaac integration index](../../isaac/README.md) lists other helpers. In Isaac Sim, open the intended graph, press Play, and check one link at a time: received Twist, differential output, articulation wheel commands, and actual base movement. For sensors, check render product, publisher node, message payload, and timestamp. Isaac Sim 6.1 can migrate old node types in memory and mark a stage unsaved; review the resulting diff before saving the canonical scene.
