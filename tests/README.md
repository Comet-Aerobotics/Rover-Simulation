# Verification map

| Test | Runs where | Status |
|---|---|---|
| `ros2/cometbot_ws/src/cometbot_control/test/test_mapping.py` | Headless Python; no ROS runtime | Six tests passed locally |
| `tests/integration/test_camera_graph.py` | Headless Python with `usd-core` | Checks canonical graph and detects bad camera position, target, and render-product wiring |
| `tests/terrain/test_generate.py` | Headless Python with NumPy | Three tests passed under Python 3.12 |
| `terrain/validate.py` | Isaac Sim Python or compatible `usd-core`; reads saved USD | Passed: mesh topology, both collision APIs, single collider, no rigid body, inactive Cube_003 |
| `isaac/diagnostics/set_rover_mass.py` | Isaac Sim Python or compatible `usd-core`; writes a separate USD | Creates a 55 kg candidate from configured total mass and composed wheel masses |
| `isaac/diagnostics/validate_action_graph.py` | Isaac Sim Python or compatible `usd-core`; reads saved USD | Checks rover graph plus camera target, pose, clipping, depth/RGB topics, frame IDs, and render-product wiring; it does not verify live messages |
| `isaac/diagnostics/validate_action_graph.py --local-jackal scenes/CAMERASYNCSSMOETIMES.usd` | Isaac Sim Python or compatible `usd-core`; reads canonical USD | Confirms controller tokens match four composed local revolute joints |
| `isaac/diagnostics/prepare_local_jackal_scene.py --output scenes/CAMERASYNCSSMOETIMES_LOCAL_JACKAL_REBUILT_CANDIDATE.usd` | Isaac Sim Python or compatible `usd-core`; writes a new USD beside canonical scene | Rebuild utility refuses to overwrite existing USD files |
| `scripts/windows/start_rover.ps1 -Mode Diagnostics` | Windows host, WSL, Docker, usbipd | Read-only except it may wake the selected WSL distro and attach one uniquely identified Stadia device |
| Cross-host DDS delivery | Windows Isaac + WSL Docker, safe immobilized rover | Pending; no matching subscription/command observed in the current probe |
| Static wheel-terrain contact | Isaac Sim 6.1 runtime contact sensor | Passed once: front-left wheel contact observed, max measured force 13.76 N; sustained stability is unverified |
| Powered motion, terrain stability, sensor output | Isaac Sim 6.1 GUI or simulation runtime | Pending; no command-driven motion or sensor-message acceptance recorded |

Do not publish nonzero `/cmd_vel` on the active ROS domain unless the rover is safely immobilized. See [known issues](../docs/known-issues.md).
