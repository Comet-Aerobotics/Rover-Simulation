# Troubleshooting by symptom

Use the observed scene name and whether **Play** is active when reporting a failure. Check a link in the pipeline before changing physics, firewall, or sensor settings. Diagnostics are read-only unless they attach a USB controller or wake WSL.

| Symptom | First check | Next check |
| --- | --- | --- |
| Launcher reports a Bash quote or joystick enumeration error | Use current `scripts/windows/start_rover.ps1`; the PowerShell 5.1 argument fix is in the launcher | Run `-Mode Diagnostics` and confirm `/dev/input/jsN` output |
| No joystick node in WSL | `usbipd list` and attachment state | Linux HID driver and `/dev/input/js*` |
| Remote controller not discovered | Source PC online in Tailscale, `usbipd list` says `Shared`, TCP 3240 reachable | [Remote controller guide](setup/remote-controller.md); launcher does not require editing shared `.env` for each host |
| Joystick in WSL, absent in Docker | Container device bind and input-group permission | Rerun Start after attachment; inspect selected `jsN` |
| `/joy` is present but axes stay zero | Correct selected controller and Joy device ID | `config/joy.yaml`, physical axis numbering |
| Joy axes stay at `-1.0` or `1.0` while untouched | Check which `/dev/input/jsN` the launcher selected and its HID driver binding | [Remote controller guide](setup/remote-controller.md); Joy-Con 2 may need its protocol driver even when a `jsN` node exists |
| Split controller has only one active side | Check both `/joy_left` and `/joy_right` and select left device first, right device second | For Joy-Con 2, select both USB devices and use pair mode; see [remote controller guide](setup/remote-controller.md) |
| `/joy` changes but `/cmd_vel` stays zero | `config/controller.yaml` axis 1/3, deadzone 0.1, 0.5 s freshness | `teleop_publisher` log and optional enable button |
| `/cmd_vel` exists but Isaac has no subscriber | Press Play, confirm ROS 2 Bridge loaded | Same domain/Fast DDS in the **existing** Kit process; restart Kit to change its environment |
| Subscriber exists but rover does not move | Both saved drive graphs and articulation target | Wheel joint names, rigid-body mass/contact, actual nonzero Twist |
| Rover floats or jitters on normal ground | One static terrain collider, `approximation = none` | Wheel collider, mass, other overlapping colliders |
| Sand mode does not form ruts | Fresh Kit launch with `-SandDeformation`, generated sand stage, `AIAA_SAND_READY` | `terrain/validate_sand_scene.py`, wheel hit on sand rather than rock |
| Sand mode moves but camera output collapses | Confirm visible tile representation; older scene may still use full-mesh writes | Rebuild sand candidate with `--overwrite` after saving/closing it |
| Lidar `/scan` exists but rays/points are absent in viewport | Saved lidar `drawLines` and `drawPoints` are true | Reload scene; viewport display and ROS publishing are separate |
| RGB/depth topic exists but image is wrong | Receive one actual frame and inspect pixels, dimensions, timestamp | OAK camera prim, 640 × 400 render product, `/ActionGraph` |
| PoseTree warning | Inspect actual `/tf` message and frame tree | Camera/laser prim paths; warning alone did not prove missing TF in prior test |
| GUI FPS is low | Record viewport resolution and scene/physics setting | [Performance analysis](performance-analysis.md): GPU physics and camera rendering had measured costs |
| Invisible obstacle | Inspect active collider at stop location | CurvedWall/Cube_003 state, rock/door/wall colliders; bounds are only screening evidence |
| Scene looks changed after opening | Check unsaved marker and Kit node migration | Compare composed USD/layers before saving |

The earlier Windows-to-WSL ROS session did deliver controller-driven motion and real sensor messages in the 55 kg candidate. A later session with an already-running Kit process had zero Isaac `/cmd_vel` subscribers. Recheck the current process instead of treating either snapshot as permanent. Use [launch](setup/launch.md), [rover](rover.md), [sensors](sensors.md), [terrain](terrain.md), and [ROS 2](ros2.md) for subsystem details.

`scripts/diagnostics/runtime_report.ps1` gives a broad host/WSL/Docker snapshot, but its embedded WSL shell commands predate the launcher's quoting fix. If a field looks incomplete, compare it with `start_rover_all.ps1 -Mode Diagnostics` and a direct WSL check.
