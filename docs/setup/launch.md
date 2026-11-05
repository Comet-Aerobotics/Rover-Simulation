# Rover launch and shutdown

This launch guide targets the consolidated simulation-only ROS stack. It does not start physical CAN/micro-ROS hardware or the optional Foxglove/MCP services.

## Diagnostics first

From PowerShell at the repository root:

```powershell
.\scripts\windows\start_rover.ps1 -Mode Diagnostics
```

`start_rover_all.ps1` is the familiar legacy-name entry point and forwards to the same supported launcher. Running it without arguments starts the combined stack; pass `-Mode Diagnostics` to inspect without starting it. Use `start_isaac_sim.ps1` to open only Isaac Sim with the canonical scene and Fast DDS environment, without starting Docker or ROS. It loads `scenes/CAMERASYNCSSMOETIMES.usd` through Isaac Sim's startup `--exec` Python hook. Set `ROVER_SCENE` in `.env` or pass `-Scene` to select another scene. If Isaac Sim is already open, the script leaves it untouched and exits; save your current stage before opening another scene manually.

The launcher creates `_aiaa_rover_simulation_repo` as a junction under the Isaac Sim install and points it at this repository. Kit's `--exec` parser splits script paths at spaces, so the launcher passes the helper through this no-space junction. It refuses to reuse an existing alias if it points somewhere else. The selected scene path remains in the child process environment.

The script wakes Ubuntu, checks USB attachment, inspects the WSL Docker engine and ROS nodes, and does not start nodes. Use the WSL context: the Windows Docker CLI may point at a separate `desktop-linux` context.

## Avoid duplicate control nodes

If diagnostics reports `/joy_node` or `/teleop_publisher` under the old `cometbot_dev`, stop only that control launch and re-check:

```powershell
.\scripts\windows\stop_rover.ps1 -Container cometbot_dev
.\scripts\windows\start_rover.ps1 -Mode Diagnostics
```

The stop script sends SIGINT only to the named launch/node processes; it leaves the container and Isaac Sim open. It does not save or close stages.

## Start the consolidated stack

```powershell
.\scripts\windows\start_rover.ps1 -Mode Start
```

It builds/starts `aiaa_rover_dev` from `docker/compose.yaml`, opens WSL and ROS terminals plus `/joy` monitoring, launches the canonical USD when Isaac Sim is not already open, and checks expected ROS nodes/topics. A present `/cmd_vel` publisher/subscriber does not establish Windows-to-WSL delivery. Confirm Bridge startup and subscriber matching in Isaac Sim, then run safe, immobilized-rover end-to-end tests before motion.

## Shutdown

```powershell
.\scripts\windows\stop_rover.ps1
```

Shutdown stops this project's teleop processes only. The WSL Docker engine, containers, and Isaac Sim remain available. Close/save Isaac Sim interactively if there are unsaved stage edits.

## Original launcher disposition

`start_rover_all.ps1` is represented by the compatibility entry point and the consolidated `start_rover.ps1`. `start_stack_fixed.ps1` is kept in `legacy/archived_scripts/`: its Isaac environment setup is available through `start_isaac_sim.ps1`, while its MCP server and local LLM startup are unrelated to the rover simulation and are intentionally excluded. The earliest `start_stack.ps1` remains preserved in the adjacent source archive because it has the same unrelated services and hard-coded machine paths.
