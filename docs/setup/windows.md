# Windows host setup

The observed installation uses Isaac Sim 6.1 at `C:\isaac-sim\_build\windows-x86_64\release`, WSL Ubuntu, Docker accessible from WSL, and `usbipd-win` for controller attachment. Local paths and ROS environment overrides belong in `.env` (copy `.env.example` first). Check the selected scene and controller before launching a live drive.

| Requirement | Why | Check |
| --- | --- | --- |
| Isaac Sim 6.1 and bundled ROS Humble libraries | Scene/graph compatibility and Windows Bridge | `ISAAC_SIM_ROOT`, launcher output, Isaac extension log |
| WSL 2 Ubuntu | Hosts Docker CLI and Linux input device | `wsl.exe --list --verbose` |
| Docker engine from Ubuntu | Runs `aiaa_rover_dev`; Windows CLI may target another context | `wsl.exe -d Ubuntu --exec docker context show` |
| USB/IP controller path | Exposes `/dev/input/jsN` to `joy_node` | `usbipd list`, then launcher Diagnostics |
| Fast DDS and matching ROS domain | Windows Isaac and WSL ROS participants must discover each other | `.env`, Compose environment, Kit startup log, ROS topic subscriber count |

From the repository root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\scripts\windows\start_rover_all.ps1 -Mode Diagnostics
.\scripts\windows\start_rover_all.ps1
```

The launcher selects bundled Humble, `rmw_fastrtps_cpp`, and domain 0 by default, and clears stale DDS profile overrides before starting Kit. An existing Kit process keeps its original ROS environment and scene, so close it after saving changes before testing a new scene or domain. `start_rover_all.ps1 -SandDeformation` needs the generated sand stage and a fresh Kit launch. See [launch](launch.md).

The Windows launcher supports local USB devices and discovers online Tailscale peers exporting USB/IP devices. It prompts for the host or device when there are multiple choices and stores that computer's selection in its ignored `.env`; shared repository files do not contain per-person hostnames or bus IDs. For the full remote controller setup, including usbipd-win, Tailscale firewall access, Linux HID drivers, and the Joy-Con 2 split-pair caveat, see [remote controller setup](remote-controller.md). A controller appearing in WSL does not prove Linux HID support, container access, or ROS Joy axis mapping works. Use Diagnostics and [ROS checks](../ros2.md) in that order.
