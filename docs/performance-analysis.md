# Isaac Sim performance investigation

Measured November 6, 2026, on the 55 kg rover scene in Isaac Sim 6.1. The operator reported about 16 FPS in the GUI. Computer Use access to the Kit window was denied, so its in-app profiler and FPS counter could not be read directly. All controlled changes below were made in memory in separate headless processes; the open GUI and the modified scene file were left untouched. The headless process used the base Python experience with `isaacsim.ros2.bridge` explicitly enabled, Fast DDS on isolated ROS domain 44, and the same saved scene. The GUI remained open and competed for the GPU throughout. Treat the A/B frame times as evidence of relative cost, not a prediction of GUI FPS.

## Hardware and scene inventory

- Threadripper PRO 7975WX: 32 cores / 64 logical processors; approximately 256 GiB RAM. The live Kit process used about five core-equivalents in one three-second sample, far below whole-CPU saturation.
- RTX A4000: 16.4 GB VRAM, approximately 7.4 GB used by the running GUI; sampled GPU utilization 67–78%, power about 97–101 W, temperature 75–78 °C. NVIDIA reported no active thermal or power throttling. VRAM exhaustion was not observed.
- The saved stage has 70 render meshes and about 1.90 million triangles. The terrain alone has 1,296,702 triangles on a 1 cm grid and is the sole large static triangle-mesh collider. There are 25 enabled colliders total.
- Three authored render products: 1280×720 viewport, 640×400 OAK camera, and a second 640×480 product pointing at the same OAK camera. Seven lights and seven OmniGraph hierarchies are present. Two drive graphs both subscribe to Twist and target the rover articulation.
- `/physicsScene` uses 60 physics steps/s, GPU dynamics, and GPU broadphase. The OAK camera has no authored `OmniSensorAPI` tick rate. RGB and depth were observed through ROS during the controlled runs.

The working 55 kg USD differs from Git HEAD mainly in saved viewport camera pose and several visibility opinions. Restoring the earlier, farther viewport pose in memory changed frame time by 8–9 ms. This is a real view-dependent cost, but the in-memory GUI view may differ from either saved pose.

## Controlled timing

Each main comparison used 60 warmup frames followed by 90–120 measured frames. `SimulationApp.update()` was timed around the complete frame. A 120-frame measurement advances simulation time by 2 s. The GUI continued using the GPU, so individual runs have some noise. Repeated GPU and CPU baselines stayed close.

| In-memory condition on the 55 kg scene | Mean frame time | Throughput | Interpretation |
| --- | ---: | ---: | --- |
| GPU physics, all graphs, ROS bridge | 81.3 ms | 12.3 FPS | Controlled baseline |
| CPU physics with MBP, all graphs, ROS bridge | 30.4 ms | 32.9 FPS | Largest measured gain; no render or sensor disabled |
| CPU physics, OAK tick rate 10 Hz | 22.9 ms | 43.7 FPS | RGB/depth still published at approximately 9–10 Hz over the full test interval |
| CPU physics, viewport 960×540 | 25.0 ms | 40.1 FPS | OAK sensor resolution unchanged |
| CPU physics, OAK 10 Hz, viewport 960×540 | 17.8 ms | 56.2 FPS | Combined trial; GUI result must be measured separately |
| CPU physics, camera graph off | 21.3 ms | 46.9 FPS | Camera pipeline costs roughly 9 ms at default cadence |
| GPU physics, earlier far viewport pose | 73.2 ms | 13.7 FPS | Current closer view adds about 8 ms |
| GPU physics, lidar prim and graph off | 82.1 ms | 12.2 FPS | No measurable headless gain; GUI ray/point overlay remains untested |
| GPU physics, all graphs off | 21.9 ms | 45.7 FPS | Playback graph or active-articulation work dominates paused cost |
| GPU physics, both drive graphs off | 30.6 ms | 32.7 FPS | Either drive graph alone keeps the rover active and costs 74–79 ms total |

The CPU-physics and GPU-physics runs settled the base link at approximately 0.0329 m and 0.0333 m in Z respectively after the same simulation duration. In a separate isolated ROS test, a 0.5 m/s Twist command moved the rigid-ground rover 1.20 m under CPU physics versus 1.27 m under GPU physics over three simulated seconds. CPU physics preserves powered movement, but the roughly 5% travel difference still calls for handling validation. Both RGB and depth published with the ROS bridge enabled: 57–58 messages per topic over three simulated seconds at the default cadence; the 10 Hz camera trial delivered 28 per topic over the same warmup-plus-measurement interval. The 640×480 render product had no measurable effect when deactivated alone; the graph may recreate or ignore it.

## Terrain collider isolation

With only one drive graph active, the full 1 cm terrain collider measured 79.4 ms/frame. Disabling its collision in memory reduced this to 36.6 ms, but the rover then lacked ground support, so this is an upper bound on contact cost. Keeping terrain support with a collision-only decimated mesh gave:

| Collision grid | Collider triangles | Mean frame time |
| --- | ---: | ---: |
| 1 cm original | 1,296,702 | 79.4 ms |
| 2 cm proxy | 325,000 | 72.3 ms |
| 5 cm proxy | 52,000 | 68.6 ms |
| 10 cm proxy | 13,000 | 60.3 ms |

The visible 1 cm terrain mesh was unchanged in these proxy tests. A 10 cm collision grid is coarse relative to the 9.8 cm wheel radius and requires traction, obstacle, sinkage, and slope acceptance before use. Built-in `meshSimplification` measured 72.8 ms, similar to the 2 cm proxy. CPU physics offers a larger gain without lowering ground resolution.

## Sand-mode finding and repair

The original sand scene rendered one 650,000-point terrain mesh while updating small collision tiles. A stationary rut benchmark missed a driving failure. With the ROS bridge enabled and a 0.5 m/s Twist command for three simulated seconds, static sand tiles moved the rover 1.03 m, but the full rut runtime moved it only 0.0085 m. A visual-only full-mesh update yielded zero measured travel. At a 10 Hz OAK rate over four simulated seconds, RGB/depth delivery fell from 38 pairs with static tiles to 5–6 pairs with full-mesh updates. Updating only the small collision tiles preserved 0.92 m travel, 38 RGB/depth pairs, 81 scans, and a 2.8 cm rut. This isolated the regression to the large rendered-mesh write; the exact renderer or physics invalidation mechanism remains unprofiled.

The repaired builder removes the original mesh faces but keeps its points as the undeformed reference. It renders the same 176 small tiles used for collision and updates only touched tiles. Isolated headless ROS results with a 0.5 m/s command for three simulated seconds were:

| Sand scene, 10 Hz OAK | CPU dynamics + MBP | GPU dynamics + GPU broadphase |
| --- | ---: | ---: |
| Rover travel | 0.91–0.93 m | 1.07 m |
| RGB/depth pairs | 38 | 38 |
| Laser scans | 81 | 81 |
| Maximum rut depth | 2.8–2.9 cm | 3.0 cm |
| Mean headless frame time | 24.1–24.2 ms | 79.3 ms |

A captured 640×400 RGB frame contained terrain imagery, and a runtime restart reconstructed the rutted height grid from tile geometry with zero measured height difference. These tests do not establish visual rut quality or controller feel in the GUI. The GUI remained open during the headless tests, and CPU/GPU travel differences include physics-setting and startup effects; they are not a soil calibration result.

## Recommendations

1. **First trial: CPU physics + MBP broadphase in a separate scene candidate.** Keep the original scene. Validate controller steering, wheel contact, `/scan`, RGB/depth, and TF in the GUI before promotion. NVIDIA [recommends CPU simulation for scenes with a few rigid bodies or articulations](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/110.0/dev_guide/guides/physics-performance.html). This recommendation would need revisiting if GPU-only grains, deformables, or particles replace the empirical sand model.
2. **Set an OAK sensor tick rate according to the required perception rate.** The measured 10 Hz setting retained RGB/depth publication and reduced frame time. Isaac Sim 6.x [uses `OmniSensorAPI` tick rates](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_multitick_rendering.html); the older helper `frameSkipCount` is deprecated in the [ROS 2 sensor migration guide](https://docs.isaacsim.omniverse.nvidia.com/latest/migration_guides/isaac_sim_6_0/ros2_sensor_graph_migration.html). Confirm image content and timestamp cadence with the downstream stack.
3. **Use a smaller operator viewport if visual detail permits.** The 960×540 trial was a useful compromise. Keep the OAK render product's 640×400 resolution independent of viewport size.
4. **Check sand handling and rut appearance in the GUI.** The local tile repair passed powered ROS travel and sensor cadence in headless runs. Soil coefficients and nominal wheel loads still need measurements from the intended sand.
5. **Defer collider simplification until after CPU physics acceptance.** It trades terrain fidelity for smaller gains in the GPU trials. Keep lidar enabled; its sensor/graph ablation did not improve headless throughput. Remove the duplicate drive graph only after identifying which one supplies the proven controller path; the duplicate is a correctness concern more than the principal FPS cause.
6. **Profile the actual GUI after applying one change at a time.** NVIDIA's [Tracy guide](https://docs.isaacsim.omniverse.nvidia.com/latest/utilities/debugging/profiling_performance.html) distinguishes physics steps, graph execution, and GPU render waits. The live window could not be instrumented here because Computer Use access was denied.

The headless logs also showed unresolved texture references during stage load and repeated PoseTree warnings with ROS enabled. Their per-frame cost was not isolated; the ROS-enabled CPU baseline remained close to the earlier CPU baseline without ROS. They warrant separate visual/TF checks, not prioritization over the measured physics setting.
