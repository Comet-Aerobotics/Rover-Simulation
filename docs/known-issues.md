# Known issues and validation status

Updated 2026-11-05 after checking the running WSL ROS stack, the open 55 kg candidate stage, the saved USD layers, and the user's live controller test.

## Confirmed and actionable

- **Lidar rays and points were hidden in the viewport.** `/jackal/base_link/laser/Lidar` is present and enabled, but the shared Jackal USD had `drawLines = false` and `drawPoints = false`. Both are now `true` in `assets/robots/jackal/ros2_jackal_PhysX_vlp16.usd`. The canonical and 55 kg candidate scenes inherit the corrected values. Reload the open stage after saving any unrelated unsaved edits to see the change; the current in-memory stage was not modified. This display setting is separate from `/scan` publication, which passed below.
- **The old stop script could stop teleop in another container.** `cometbot_dev` uses the host PID namespace, so its former `docker exec ... pkill` commands also matched processes in `aiaa_rover_dev`. `scripts/windows/stop_rover.ps1` now selects PIDs from `docker top` for the named container before signaling them. The intended Joy and teleop nodes were restarted and the legacy control nodes were stopped; both containers remain running.

## Still unverified, with a specific reason to check

- **Sand calibration and live driving acceptance:** the new opt-in sand scene makes wheel ruts in the rendered and colliding terrain, and a headless Isaac Sim check showed the rover settling lower than on rigid ground. The soil coefficients use provisional values and nominal per-wheel load. Controller-driven travel on this sand scene and agreement with physical sand measurements remain to be checked; see `docs/terrain.md`.
- **Camera acceptance:** RGB, depth, and camera-info messages reached WSL, and the saved camera pose and graph passed structural checks. Image content, camera-info calibration values, and physical mount calibration have not been measured. These are requirements only if the camera feed is part of the current simulation goal. Physical calibration requires a real camera reference.
- **Canonical-scene dynamics:** the user confirmed controller-driven motion in the open `scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd`. That does not establish powered motion or prolonged contact behavior in the separate canonical scene. The candidate's 55 kg mass should be promoted only if its settling and handling are preferable in a comparison.

## Previously listed items that are not current blockers

- **Controller path and cross-host DDS:** after cleanup, `aiaa_rover_dev` has one `/joy` publisher and one `/cmd_vel` publisher. The current WSL graph sees two Isaac `/cmd_vel` subscribers, and the user confirmed the rover moves with controller input. The earlier zero-subscriber snapshot did not describe the later working session. The Windows inbound firewall was only a proposed barrier; no firewall change is justified.
- **ROS sensor delivery:** `/scan`, `/tf`, `/oak_d/rgb/image_raw`, `/oak_d/depth`, and `/oak_d/rgb/camera_info` are advertised in WSL. One actual laser scan, RGB frame, depth frame, camera-info message, and TF message were received. Message content and sustained rates were not evaluated.
- **PoseTree warnings:** an earlier Isaac Sim log repeatedly reported `target getObjectType eInvalid` for `/jackal/base_link/laser` and camera frames. A subsequent `/tf` message includes `laser` and those camera frames, so the warning is not presently evidence of missing TF. It also does not explain the hidden lidar rays and points.
- **Docker input access:** `aiaa_rover_dev` can open both `/dev/input/js0` and `/dev/input/event0`; Joy and teleop are running. The older stale bind-mount issue was repaired.
- **Legacy container:** `cometbot_dev` remains running for unrelated legacy work, with its duplicate Joy and teleop processes stopped. Its mere presence is not a rover issue.
- **Wall normal map:** the stale BlackPaint UI default was already corrected to an existing project texture.
- **Wheel-controller limits:** the numeric limits look stage-scaled, but the user reports normal controller response. Do not retune them on the basis of their raw values alone.
- **USDC crate warnings:** several older referenced assets emit 0.7.0 deprecation warnings in standalone `usd-core`, but both scenes compose and render in Isaac Sim 6.1. This is a future format-maintenance concern, not an observed runtime failure.
- **Automatic node migration:** Isaac Sim 6.1 migrates old graph node types in memory and marks the stage unsaved. The saved graphs pass structural checks. Do not save the open stage solely to clear a migration marker; review any intended stage changes first.

## Evidence and limits

- The open candidate stage was identified from the running Isaac Sim window title. The user verified rover motion and specified that the missing lidar feature is the viewport ray/point display.
- The saved lidar is enabled, with a 360-degree horizontal field of view, and its `IsaacReadLidarBeams` output is connected to `ROS2PublishLaserScan`. The publisher uses the node's default `scan` topic name, observed live as `/scan`.
- The shared lidar USD changed only in `drawLines` and `drawPoints` under a semantic before/after comparison. Both scenes pass `validate_action_graph.py` after the edit. Six ROS mapping tests and three terrain tests pass; four integration placeholders remain skipped.
- Computer Use access to the Kit window was denied, so the updated ray/point display was verified in the saved composition, not visually in the live viewport. The open stage has an unsaved marker and was left untouched.
