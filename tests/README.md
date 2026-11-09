# Verification map

Tests and validators answer different questions. Pure Python tests cover mapping and terrain math; USD audits inspect saved structure; a running Isaac Sim scene is needed for contact, sensors, and controller behavior.

| Check | Command or file | What it establishes |
| --- | --- | --- |
| Joystick mapping | `pytest ros2/cometbot_ws/src/cometbot_control/test/test_mapping.py` | Axis selection, shaping, deadzone, and missing-input behavior |
| Terrain processing/model | `pytest tests/terrain/` | DEM grid and rut-field math |
| Camera graph test | `pytest tests/integration/test_camera_graph.py` with USD bindings | Saved target, pose, and graph configuration; not pixels |
| Normal terrain audit | `py terrain/validate.py scenes/CAMERASYNCSSMOETIMES.usd` | DEM parity, topology, ground and rock colliders |
| Sand terrain audit | Isaac Python `terrain/validate_sand_scene.py` | Visible/colliding tile structure, seams, bounds |
| Action Graph audit | `py isaac/diagnostics/validate_action_graph.py ...` with USD bindings | Saved intended drive/camera wiring |
| Launcher diagnostics | `.\scripts\windows\start_rover_all.ps1 -Mode Diagnostics` | WSL, Docker, controller, and node visibility |
| Runtime acceptance | Isaac Sim Play plus controller/sensor checks | Actual rover motion, ground contact, image/scan/TF content |

Install the relevant extras with `py -m pip install -e ".[terrain,usd-audit,test]"`. Use Isaac Sim's Python for scripts that initialize Kit; a bare `python.bat` does not automatically expose `pxr` until the application is initialized. Record the tested scene variant, physics setting, ROS domain, and whether the result was structural, headless, or GUI. See [known issues](../docs/known-issues.md) and [performance analysis](../docs/performance-analysis.md) for measured results and outstanding acceptance.

For local Windows mapping tests outside the ROS container, first set `$env:PYTHONPATH=(Resolve-Path 'ros2/cometbot_ws/src/cometbot_control').Path`; the ROS package is otherwise not on Python's import path. Then run `py -m pytest tests/terrain ros2/cometbot_ws/src/cometbot_control/test`.
