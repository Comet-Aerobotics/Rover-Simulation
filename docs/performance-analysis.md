# Isaac Sim performance investigation

Measured November 6–10, 2026, on the 55 kg rover scene in Isaac Sim 6.1. The operator reported about 16 FPS in the GUI. The November 9 live sand window showed 10.9–11.9 FPS while playing, with lidar rays displayed. The older controlled results below used separate headless processes; the November 10 results include fresh **full-GUI Kit** processes with the sand scene playing. Four full-GUI Tracy traces were captured for the OAK/timeline comparison below. On November 13, CPU dynamics with MBP broadphase became the saved rover-scene and launcher default; the original GPU results remain historical comparison data.

## November 10: Tracy trace separates camera work from timeline scheduling

The earlier OAK-on/off comparison was confounded: with the OAK graph enabled, Kit changed `/app/player/useFastMode` from `false` to `true` at Play. With the graph disabled before Play, it remained `false`. At the end of the same-length probes, the enabled case had advanced about three times as much simulation time (31.21 versus 10.42 seconds). NVIDIA's [multi-tick timing guide](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_multitick_rendering.html) explains that fast mode bypasses timeline subsampling when the run loop exceeds stage `timeCodesPerSecond`; this can speed simulated time relative to wall time. The exact code path that toggles fast mode when this graph is active has not been isolated.

All four fresh processes used the same sand scene, CPU PhysX/MBP, rut runtime, 10 Hz OAK prim setting when active, ROS bridge, and 72 Hz run-loop limit after Play. Tracy was launched with CPU and GPU profiling settings; the exported comparison below uses CPU zones. The table reports the final 250 steady `App Main loop` CPU zones in each trace. The FPS column comes from 600 GUI update intervals in the same run. The matched pairs were changed **in memory** only.

The automated probes launched the full Kit GUI experience with its viewport render path active and a hidden-window process setting. Profiling adds overhead, and a hidden window can differ from an operator's visible session; use the matched differences to diagnose the cause, then confirm absolute FPS in the visible controller workflow.

| OAK graph | Timeline fast mode | Main loop, last 250 frames | Overall GUI FPS | Physics updates per 250 frames |
| --- | --- | ---: | ---: | ---: |
| On | True (Kit's Play behavior) | 22.68 ms | 43.9 | 200 |
| Off | False (Kit's Play behavior) | 16.10 ms | 61.5 | 66 |
| On | False (forced after Play) | 17.24 ms | 57.7 | 67 |
| Off | True (forced after Play) | 20.43 ms | 48.7 | 200 |

Thus the natural 6.58 ms/frame gap is **not** a pure camera rendering cost. Matching fast mode reduces the OAK-on penalty to 1.14 ms/frame with fast mode off or 2.25 ms/frame with fast mode on. The remaining differences include camera render-product work, ROS writers, and interactions with other graph/render work. Across the natural pair, `ExecutionController::execute` ran on 250 versus 83 of the selected GUI frames, accounting for 10.73 versus 3.40 ms per GUI frame; `PhysXUpdateNonRender` ran 200 versus 66 times and accounted for 4.99 versus 1.67 ms per GUI frame. These are overlapping Tracy zones, so their durations must not be added. When fast mode was matched off, physics ran 67 versus 66 times, the execution-controller difference fell to 0.25 ms/frame, and the CPU `SceneRenderer-rtx: render` zone differed by 1.12 ms/frame. With fast mode matched on, the corresponding renderer difference was 1.21 ms/frame. The trace identifies scheduling as the main reason for the large apparent camera penalty; it does not prove that the GPU renderer or image writer is individually free of stalls. See NVIDIA's [Tracy zone guide](https://docs.isaacsim.omniverse.nvidia.com/latest/utilities/debugging/profiling_performance.html).

An additional full-GUI, camera-on trial forced fast mode off and sent a 0.5 m/s ROS Twist while receiving sensor data. It averaged 17.53 ms / 57.0 FPS over 240 measured updates, received 39 RGB images, 39 depth images, and 32 lidar scans during the run, and formed a 7.7 mm rut. This establishes powered movement and continued camera/lidar delivery in that temporary mode. It does not validate exact ROS timestamp alignment, sensor rate, or handling equivalence, so the launcher still retains its previous default. The traces and export summary are in ignored `work/tracy_*.tracy` and `work/tracy_analysis.txt`; no USD scene was saved by these probes.

## November 10: simulation-side GUI bottleneck

CPU physics, 10 Hz OAK sensor scheduling, 10 Hz rotating PhysX lidar, and a single drive graph brought a powered headless sand run to 14.5–15.8 ms/frame (about 63–69 FPS). The same scene in full GUI Kit still measured about 40–45 FPS while playing. An empty full-GUI stage measured 111 FPS, so the remaining limit comes from scene work. The GUI probe used Kit's update event stream to time every frame after 90 warmup frames (240 measured frames per condition). It played the sand scene with ROS bridge and rut runtime attached but did **not** command rover movement; powered movement and sensor delivery were checked separately in headless Kit. Individual GUI runs vary by several FPS, so small differences should not be treated as wins.

| Fresh full-GUI condition | Mean frame time | FPS | What it isolates |
| --- | ---: | ---: | --- |
| Empty stage | 9.03 ms | 110.7 | Full application overhead without this scene |
| Sand scene paused, all geometry visible | 13.26 ms | 75.4 | Scene rendering without playback |
| Sand scene playing, full OAK/ROS/physics | 22.35–24.98 ms | 40.0–44.7 | Current optimized full-feature run |
| OAK camera graph off before Play | 16.21 ms | 61.7 | Removes camera work and changes Play-time timeline scheduling |
| All OAK image/info writers disabled, render-product node retained | 17.02 ms | 58.8 | Changes both writer attachment and scheduling; not a pure writer cost |
| OAK render-product node disabled before Play | 16.20 ms | 61.7 | Changes render-product work and scheduling together |
| RGB writer only / depth writer only | 24.37 / 24.26 ms | 41.0 / 41.2 | Either image stream keeps the slower natural scheduling condition |
| PhysX sand-tile collision replaced in memory by one support plane | 18.27 ms | 54.7 | 176 detailed colliders cost several ms; this is a fidelity-breaking upper bound |
| All authored graphs off before Play | 14.29 ms | 70.0 | Combined graph/sensor work; this condition cannot drive or publish ROS data |

At the same full-GUI settings, lidar off, lidar overlay off, smaller viewport render product, hidden sand geometry, and all lights off each changed FPS by at most a few frames. Lowering OAK tick rate from 10 to 5 or 2 Hz also did not materially change GUI FPS (44.4, 43.4, and 45.1 FPS respectively), although headless RGB/depth delivery fell from 36/36 to 6/6 messages across four simulated seconds when changed from 10 to 2 Hz. Limiting `/ActionGraph/OnTick` to every sixth update and disabling the extra saved `Replicator` render product likewise did not help. Those ablations leave the active camera's Play-time fast-mode change in place; the matched Tracy comparison above gives the more useful estimate of camera work. NVIDIA documents the camera sensor tick rate and [render-product scheduling](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_multitick_rendering.html).

The supported launcher now sets OAK to 10 Hz and offers `-NoOak` for fast controller sessions. Rover scene layers deactivate the imported duplicate drive graph even when opened directly. The camera-off mode keeps lidar, TF, clock, physics, and sand active; RGB/depth/CameraInfo are unavailable until a fresh launch with OAK enabled. Clean full-GUI camera-off runs measured 58.0 and 61.7 FPS; a full-GUI camera-off run sending a 0.5 m/s ROS Twist measured **56.0 FPS** and formed a 6.0 mm rut. Thus **60 FPS is not yet consistently met**. A powered headless camera-off run moved 1.28 m, made a 6.6 mm rut, and delivered 38 full laser scans, 239 clock messages, and 239 TF messages over four simulated seconds. The shared Jackal asset now rotates its PhysX lidar at 10 Hz instead of firing a full sweep each physics step. Full 900-range `/scan` messages were observed with `scan_time = 0.1 s`. The saved asset's semantic USD content changed only in `rotationRate`. On headless powered sand runs, the 10 Hz sweep gave a 4 ms/frame gain in one A/B pair but almost no gain in another with a different GUI workload, so it is a scan-model correction and situational optimization rather than the main GUI fix. Disabling the competing drive graph also changed straight travel from about 0.93 m to 1.28 m over the measured command, making it a correctness fix.

Camera-off GUI controls with the sand runtime omitted still measured 57.9 FPS, so its idle update loop does not explain the shortfall. Keeping the visible 1 cm tiles while replacing their collider faces in memory with 2 cm or 4 cm proxies measured 56.7 FPS for both; simply reducing triangles did not help and adds a second mesh per tile. A single support plane reached 54.7 FPS **with OAK still enabled**, but removes wheel-rut contact. Collision shape count and render-product synchronization need separate profiling before changing terrain fidelity.

The saved stage uses 24 `timeCodesPerSecond` while the GUI timeline targets 60 FPS. With OAK active, the full app switched `/app/player/useFastMode` from false to true and changed its run-loop limit from 120 to 72 Hz at Play; the timeline then advanced one 24th of a second on most GUI updates. The matched trace above shows that this scheduling change explains most of the FPS gap. Setting stage time codes to 60 corrected the per-update simulated increment but left GUI throughput near 44 FPS. A forced `useFastMode=false` camera-on trial preserved driving, RGB/depth, and lidar delivery, but ROS timestamp alignment and handling equivalence need a coherent-clock check before making a persistent timing change. NVIDIA's [multi-tick timing guide](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_multitick_rendering.html) describes the full GUI's fixed-stepping and fast-mode behavior.

## Likely root cause: GPU dynamics against detailed ground

The scene originally enabled PhysX GPU dynamics and GPU broadphase for one five-link rover articulation contacting a 1,296,702-triangle terrain collider. On this small robot scene, GPU dynamics is the largest measured frame cost. The same pattern occurs with both the rigid terrain and the 176-tile deformable sand candidate. NVIDIA's [simulation performance guide](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/110.0/dev_guide/guides/physics-performance.html) says CPU simulation is often faster for a few rigid bodies or articulations; GPU simulation is aimed at large batches.

| November 9 controlled condition, ROS bridge on | Mean frame time | Throughput |
| --- | ---: | ---: |
| 55 kg rigid scene, saved GPU dynamics + GPU broadphase | 74.5 ms | 13.4 FPS |
| 55 kg rigid scene after a concurrent 10 Hz camera edit, GPU dynamics | 67.2 ms | 14.9 FPS |
| Same scene, original terrain collider replaced in memory by a plane | 45.7 ms | 21.9 FPS |
| Same scene, CPU dynamics + GPU broadphase | 30.0 ms | 33.4 FPS |
| Same scene, CPU dynamics + MBP broadphase | 29.0 ms | 34.5 FPS |
| Same scene, GPU dynamics, rover solver counts forced to 4 position / 1 velocity | 74.8 ms | 13.4 FPS |
| Sand candidate at the time of the trial, 176 visible/collision tiles and rut runtime, GPU dynamics | 76.4 ms | 13.1 FPS |
| Same saved sand candidate and runtime, CPU dynamics + MBP broadphase | 28.2 ms | 35.4 FPS |

Each run used 60 warmup frames and 90 timed frames in a fresh process; the GUI remained open. The plane trial left terrain rendering and all graphs in place, so its roughly 29 ms gain isolates detailed terrain *collision* cost under GPU dynamics. The CPU-dynamics-only trial remained near the full CPU setting, so GPU broadphase is not the main culprit. Lowering rover solver iteration counts did not help. The sand runtime rebuilt tiles and made shallow ruts in both backend trials, yet CPU dynamics still gained about 48 ms/frame. These are configuration-level A/B results; a Tracy trace would be needed to separate GPU contact kernels, synchronization, and scene writeback internally.

The 55 kg rigid candidate was edited during this investigation to add a 10 Hz OAK tick rate. A new GPU run on that revision still took 67.2 ms/frame. Its log also reported `cannot unpack non-iterable NoneType object` from both camera-info helper nodes; camera publication on that edited candidate needs validation. The earlier A/B rows used the pre-edit saved candidate, while both sand rows used the unchanged sand candidate.

The earlier GPU-mode lidar ablation found no measurable headless gain. The November 10 full-GUI ablation similarly found little benefit from removing its ray/point overlay. The repaired sand tile writes are not the main cause of the original 16 FPS result: the rigid scene without rut runtime exhibits the same GPU-dynamics slowdown.

## November 9 powered sand acceptance

CPU physics exposed a separate sand-handling problem. With a 2 rad/s spin Twist for three simulated seconds, the original rut runtime changed the rover's orientation by only 10.8°, compared with 38.6° under GPU physics. On CPU physics with the same sand tiles but no tile writes, orientation changed by about 46°; writing only the small tile point arrays also preserved turning. This isolated the loss to replacing a collision tile while a wheel was contacting it.

The CPU sand runtime now updates visible points immediately and postpones collision-tile replacement until no wheel is near that tile. A wheel does not feel its newly made rut until the tile has been cleared and rebuilt. The GPU path retains immediate collision updates. In isolated headless trials with the ROS bridge, 10 Hz camera, and both saved drive graphs active:

| Three simulated seconds | GPU physics, original rut sync | CPU physics, deferred contact rebuild |
| --- | ---: | ---: |
| 0.5 m/s straight command: mean frame time | 67.6 ms | 20.8 ms |
| Straight travel | 1.22 m | 1.09 m |
| Straight command: maximum rut depth | 7.1 mm | 6.6 mm |
| RGB / depth / scan messages, including warmup | 46 / 46 / 74 | 35 / 35 / 84 |
| 2 rad/s spin: orientation change with one drive graph | 38.6° | 45.6° |

The CPU mode rebuilt five cleared tiles during the straight run. With both saved drive graphs active, the CPU spin changed orientation by 47.4°. A separate direct-wheel trial moved 0.52 m, made a 7.0 mm rut, and found zero height difference between the runtime field and visible tile points. After Stop it measured zero depth, zero modified tiles, and zero pending tile rebuilds. The launch helper also passed an isolated check: `-CpuPhysics` applied CPU dynamics and MBP before attaching the sand runtime. The saved USD and open GUI were not changed. These tests establish powered movement and sensor delivery in headless Kit; they do not establish equal handling, exact sensor timing, or viewport FPS in the GUI. The roughly 13 cm straight-travel difference remains a handling-calibration limit.

## Hardware and scene inventory

- Threadripper PRO 7975WX: 32 cores / 64 logical processors; approximately 256 GiB RAM. The live Kit process used about five core-equivalents in one three-second sample, far below whole-CPU saturation.
- RTX A4000: 16.4 GB VRAM, approximately 7.4 GB used by the running GUI; sampled GPU utilization 67–78%, power about 97–101 W, temperature 75–78 °C. NVIDIA reported no active thermal or power throttling. VRAM exhaustion was not observed.
- The saved stage has 70 render meshes and about 1.90 million triangles. The terrain alone has 1,296,702 triangles on a 1 cm grid and is the sole large static triangle-mesh collider. There are 25 enabled colliders total.
- Three authored render products: 1280×720 viewport, 640×400 OAK camera, and a second 640×480 product pointing at the same OAK camera. Seven lights and seven OmniGraph hierarchies are present. Two drive graphs both subscribe to Twist and target the rover articulation.
- At the time of the original trials, `/physicsScene` used 60 physics steps/s, GPU dynamics, and GPU broadphase. The rover scenes now save CPU dynamics and MBP broadphase. The OAK camera has no authored `OmniSensorAPI` tick rate. RGB and depth were observed through ROS during the controlled runs.

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
| CPU physics, camera graph off | 21.3 ms | 46.9 FPS | Camera-off comparison also changes timeline scheduling; see matched Tracy results above |
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

The original sand scene rendered one 650,000-point terrain mesh while updating small collision tiles. A stationary rut benchmark missed a driving failure. With the ROS bridge enabled and a 0.5 m/s Twist command for three simulated seconds, static sand tiles moved the rover 1.03 m, but the full rut runtime moved it only 0.0085 m. A visual-only full-mesh update yielded zero measured travel. At a 10 Hz OAK rate over four simulated seconds, RGB/depth delivery fell from 38 pairs with static tiles to 5–6 pairs with full-mesh updates. Updating only the small collision tiles preserved 0.92 m travel, 38 RGB/depth pairs, 81 scans, and a 2.8 cm rut. These measurements used the earlier, deeper soil coefficients; the later shallow defaults have not had the same drive benchmark. This isolated the regression to the large rendered-mesh write; the exact renderer or physics invalidation mechanism remains unprofiled.

The repaired builder removes the original mesh faces but keeps its points as the undeformed reference. It renders the same 176 small tiles used for collision and updates only touched tiles. Isolated headless ROS results with a 0.5 m/s command for three simulated seconds were:

| Sand scene, 10 Hz OAK | CPU dynamics + MBP | GPU dynamics + GPU broadphase |
| --- | ---: | ---: |
| Rover travel | 0.91–0.93 m | 1.07 m |
| RGB/depth pairs | 38 | 38 |
| Laser scans | 81 | 81 |
| Maximum rut depth | 2.8–2.9 cm | 3.0 cm |
| Mean headless frame time | 24.1–24.2 ms | 79.3 ms |

A captured 640×400 RGB frame contained terrain imagery, and the earlier persistence behavior reconstructed the rutted height grid from tile geometry with zero measured height difference. Reset now restores the original ground by default unless persistence is explicitly enabled. These historical tests do not establish visual rut quality or controller feel in the GUI. The GUI remained open during the headless tests, and CPU/GPU travel differences include physics-setting and startup effects; they are not a soil calibration result.

## Recommendations

1. **Use the default CPU physics for sand.** Powered headless driving and steering passed with deferred collision rebuilds. The full GUI now has an automated CPU-mode frame measurement, but controller handling, visible ruts, and lidar rays still need direct operator acceptance. NVIDIA [recommends CPU simulation for scenes with a few rigid bodies or articulations](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/110.0/dev_guide/guides/physics-performance.html). Revisit this setting if GPU-only grains, deformables, or particles replace the empirical sand model.
2. **Validate realtime timeline scheduling with OAK on.** A temporary `useFastMode=false` camera-on setting raised GUI throughput from 43.9 to 57.7 FPS in a static trial and delivered RGB/depth/lidar while driving at 57.0 FPS. It also changes simulation-time progression, so compare `/clock`, image/TF headers, wall time, and controller response before making this the default. The current 24 time codes/s and 60 Hz physics step need a coherent configuration; see Isaac Sim's [multi-tick timing guide](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_multitick_rendering.html).
3. **Keep `-NoOak` for controller sessions that do not need images.** It leaves lidar, TF, clock, driving, and sand active, but its larger apparent FPS gain includes the same timeline scheduling change. With fast mode matched, camera work added about 1.1–2.3 ms/frame. Keep OAK enabled for perception work; reducing its sensor tick rate below 10 Hz did not solve the GUI cost. The 10 Hz default still controls image cadence, per Isaac Sim's [multi-tick rendering guide](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_multitick_rendering.html). The older helper `frameSkipCount` is deprecated in the [ROS 2 sensor migration guide](https://docs.isaacsim.omniverse.nvidia.com/latest/migration_guides/isaac_sim_6_0/ros2_sensor_graph_migration.html).
4. **Check sand handling and rut appearance in the GUI.** The tile repair passed powered ROS travel and sensor delivery in headless runs. Soil coefficients and nominal wheel loads still need measurements from the intended sand. A simple plane would gain several GUI FPS but remove wheel-rut contact, so it is only an ablation.

The headless logs also showed unresolved texture references during stage load and repeated PoseTree warnings with ROS enabled. Their per-frame cost was not isolated; the ROS-enabled CPU baseline remained close to the earlier CPU baseline without ROS. They warrant separate visual/TF checks, not prioritization over the measured physics setting.
