# Launch, scene selection, and shutdown

The supported Windows entry point is `scripts/windows/start_rover_all.ps1`, a short wrapper around `start_rover.ps1`. It starts the simulation-only ROS teleop stack and, if needed, Isaac Sim. It does not launch physical CAN/micro-ROS hardware. Use PowerShell from the repository root for the commands below.

## Choose a mode

| Command | Result |
| --- | --- |
| `.\scripts\windows\start_rover_all.ps1 -Mode Diagnostics` | Checks WSL, Docker context, USB/joystick visibility, container and ROS state; does not start teleop |
| `.\scripts\windows\start_rover_all.ps1` | Starts or reuses ROS container/teleop and launches normal Isaac scene if Kit is closed |
| `.\scripts\windows\start_rover_all.ps1 -SandDeformation` | Uses generated 55 kg sand scene and attaches live rut runtime when starting a fresh Kit process |
| `.\scripts\windows\start_isaac_sim.ps1 -Scene 'scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd'` | Isaac-only launch of 55 kg rigid-ground candidate |
| `.\scripts\windows\stop_rover.ps1` | Signals this project's Joy/teleop processes; keeps container and Isaac Sim open |

`start_isaac_sim.ps1` accepts an explicit `-Scene`; `.env` can set `ROVER_SCENE` for normal starts. Without either, the default is `scenes/CAMERASYNCSSMOETIMES.usd`. The `-SandDeformation` switch selects `scenes/in work/CAMERASYNCSSMOETIMES_55KG_SAND_CANDIDATE.usd` and takes precedence over the normal scene setting. That generated file must exist; [terrain](../terrain.md) has build/validate commands.

## Start sequence and what each check proves

1. The script reads `.env`, wakes the chosen Ubuntu WSL distro, and queries Docker **inside WSL**. The Windows Docker CLI may point at another context.
2. On Start, it checks local USB devices and discovers online Tailscale peers exporting USB/IP devices, then enumerates `/dev/input/jsN` in WSL. It asks which host/device to use when multiple choices are available and saves the selection in the local, ignored `.env`; no machine-specific settings need to be committed. If more than one joystick is present, Start can select one or a split-controller pair. The chosen node(s) are checked for readability inside Docker. For source-PC sharing, drivers, and Joy-Con 2 setup, see [remote controller setup](remote-controller.md).
3. It checks the separate legacy `cometbot_dev` for duplicate Joy/teleop processes, builds or reuses `aiaa_rover_dev`, and starts the selected Joy node layout and `teleop_publisher` if needed. It waits for those processes and opens WSL, Docker, and Joy monitor terminals.
4. The Isaac launcher selects bundled ROS Humble, Fast DDS, and the configured domain, then opens the chosen USD using `isaac/diagnostics/open_scene_on_start.py`. Sand mode attaches `isaac/terrain/sand_runtime.py` after the stage composes.
5. Press **Play**. The saved graphs then evaluate. Verify a nonzero Joy message, a nonzero `/cmd_vel`, an Isaac subscriber, and actual motion separately. For sensors, inspect actual image, scan, and TF payloads.

If any Isaac Sim/Kit process is already running, the launcher leaves its scene and environment untouched. This protects unsaved work but means a new `-Scene`, `-SandDeformation`, ROS domain, or middleware setting cannot take effect until you save and close the existing Kit process, then relaunch. The launcher creates a checked `_aiaa_rover_simulation_repo` junction under the Isaac installation because Kit's `--exec` parser does not accept the repository's spaced path reliably.

## Sand launch

The sand candidate is generated and ignored by Git. Close any open Isaac stage first. Then, from the repository root:

```powershell
$isaacPython = 'C:\isaac-sim\_build\windows-x86_64\release\python.bat'
& $isaacPython terrain/build_sand_scene.py --overwrite
& $isaacPython terrain/validate_sand_scene.py
.\scripts\windows\start_rover_all.ps1 -SandDeformation
```

You only need the build step when the sand scene is missing or you want a reset. Do not overwrite a sand stage with ruts you intend to keep. During Play, look for `AIAA_SAND_READY` followed by `AIAA_SAND_RUT`. See [terrain](../terrain.md) for model variables and persistence.

## Stop and recover

```powershell
.\scripts\windows\stop_rover.ps1
```

The stop script targets launch/node processes in the specified container; it does not save or close Isaac Sim. Use `-Container cometbot_dev` only when intentionally stopping old teleop processes there. If a launcher fails after starting the container, run Diagnostics, inspect `/tmp/aiaa_rover_teleop.log` inside `aiaa_rover_dev`, and check the open Kit process before launching another copy. For ROS discovery, controller, or terrain failures, use [troubleshooting](../troubleshooting.md).

For manual WSL checks, `scripts/linux/ros_health.sh` prints ROS and input state. `scripts/linux/start_teleop.sh` defaults to the legacy `/root/CAN/cometbot_ws`; set `ROS_WORKSPACE=/workspace` for this container and avoid running it alongside the Windows-owned teleop process.
