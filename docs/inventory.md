# Focused simulation inventory

**Reviewed November 8, 2026.** This inventory describes the saved canonical scene and the separately tracked 55 kg candidate. The candidate can have local modifications; record the file and revision used for a test. The adjacent `../AIAA-Isaac-Sim-Rover-source-archive/` preserves broader source intake, while `legacy/archived_scripts/` contains selected provenance only.

## Runtime components

| Component | Active source | Current saved or observed state |
| --- | --- | --- |
| Canonical stage | `scenes/CAMERASYNCSSMOETIMES.usd` | Z-up, 1 m/USD unit; local VLP-16 Jackal, corrected terrain DEM, placed-rock colliders |
| Ground | `/Lunalab/Terrain/terrain_mesh`, source DEM and `config/terrain.yaml` | 650,000 points, 1,296,702 triangles, enabled static triangle-mesh collider |
| Sand stage | Generated `in work/*_SAND_CANDIDATE.usd` | 176 visible/colliding tiles; runtime rebuilds touched tiles from wheel motion |
| Rover | `/jackal`, referenced `assets/robots/jackal/ros2_jackal_PhysX_vlp16.usd` | Four wheel revolute joints; canonical base mass authored as zero, working candidate totals about 55 kg |
| Drive graphs | `/jackal/ActionGraph`, `/jackal/ROS2_Graph/DriveGraph` | Both saved active; intended graph radius/distance 0.098/0.3755 m, duplicate uses 0.09/0.335 m |
| OAK camera | `/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB`, `/ActionGraph` | 640 × 400 active graph render product for RGB/depth; second 640 × 480 product also saved |
| VLP-16 lidar | `/jackal/base_link/laser/Lidar`, `LiDARGraph` | 360° field of view, viewport draw lines/points enabled, `/scan` publisher graph |
| Pose/time graphs | `TFGraph`, `ClockGraph`, `/ROS2_Connection_Test` | TF, odometry, and clock graph nodes saved; sampled `/tf` reached WSL |
| ROS teleop | `ros2/cometbot_ws/src/cometbot_control`, `config/{joy,controller}.yaml` | Humble `joy_node` and `teleop_publisher` in `aiaa_rover_dev`; `/joy` to `/cmd_vel` |
| Host orchestration | `scripts/windows/`, `docker/` | WSL Docker context, USB/IP joystick selection, scene launch, opt-in sand runtime |
| Lab assets | `assets/environments/lunalab/` | Room geometry, materials, seven placed rock convex-hull colliders, six ceiling lights and projector light |

The inspected 55 kg candidate had 70 render meshes and about 1.90 million triangles, of which the terrain contributes 1.30 million. It had 25 enabled colliders, seven OmniGraph hierarchies, and three saved render products. These are scene inventory counts, not FPS measurements. See [performance analysis](performance-analysis.md) for timed comparisons.

## Evidence and open acceptance

| Behavior | Evidence | Limit |
| --- | --- | --- |
| Canonical visual scene | Opened/rendered and structurally audited in Isaac Sim 6.1 | Powered handling in this exact scene is not established |
| 55 kg candidate motion | User drove the rover with controller; isolated ROS Twist trials also moved it | Does not automatically certify canonical mass/handling |
| ROS sensor delivery | Actual scan, RGB, depth, camera-info, and TF messages reached WSL in a prior running candidate | Image content, calibration, and sustained GUI rates need application-specific checks |
| Sand repair | Headless CPU and GPU drives formed ~3 cm ruts while maintaining RGB/depth/scan cadence | GUI rut appearance, controller feel, and soil calibration remain open |
| Lidar overlay | Saved asset has `drawLines` and `drawPoints` enabled | Needs visual confirmation after scene reload |
| Performance | Controlled headless tests identified GPU physics/contact and camera rendering costs | Operator GUI FPS cannot be inferred directly from those numbers |

For detailed variables, use [terrain](terrain.md), [rover](rover.md), [sensors](sensors.md), [ROS 2](ros2.md), [environment](environment.md), and [known issues](known-issues.md). `work/` and ROS `build/`, `install/`, and `log/` are generated outputs, not authoritative source files.
