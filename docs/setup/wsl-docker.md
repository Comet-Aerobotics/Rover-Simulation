# WSL, Docker, and USB controller setup

The supported ROS container is `aiaa_rover_dev`, built from `docker/compose.yaml` inside WSL Ubuntu. `cometbot_dev` is a separate legacy container; it may be stopped or running, but its Joy/teleop processes must not duplicate the new stack on the same ROS domain. The Windows launcher calls the Docker CLI in WSL because the Windows CLI may use a different context.

## Container contract

| Item | Current setting | Operational consequence |
| --- | --- | --- |
| ROS distro and middleware | Humble, `rmw_fastrtps_cpp` | Must match Isaac Sim's Bridge process |
| Domain | `${ROS_DOMAIN_ID:-0}` | Both sides need the same value |
| Network | Host mode inside WSL | DDS uses WSL host interfaces |
| Workspace | `../ros2/cometbot_ws` → `/workspace` | Container builds package and sources `/workspace/install/setup.bash` |
| Config | `../config` → `/opt/rover/config:ro` | Joy and teleop YAML available read-only |
| Input | `/dev/input` mount plus character-device read rule in the current working Compose file | Selected `jsN` device(s) must exist and be readable when teleop starts |
| DDS profile | `docker/fastdds.xml` | No historical fixed initial peer |

The launcher checks joystick visibility in WSL, selects one device or an optional pair, and probes whether the container can open them. If a running container has stale device access and no active teleop, it can recreate it. If active teleop cannot open the controller, it stops with a diagnostic rather than silently launching a duplicate node. It waits for Joy and teleop processes after starting them.

## Manual read-only checks

From PowerShell:

```powershell
usbipd list
wsl.exe -d Ubuntu --exec ls -l /dev/input
wsl.exe -d Ubuntu --exec docker ps --format '{{.Names}} {{.Status}}'
wsl.exe -d Ubuntu --exec docker exec aiaa_rover_dev ps -eo args=
```

The USB node number can change across reconnects. Use the launcher's selected `/dev/input/jsN`, not a hard-coded `js0`, when checking a new controller. The optional remote Joy-Con USB/IP path in the [remote controller guide](remote-controller.md) still requires a compatible WSL input driver before `joy_node` can see a joystick. See [ROS flow](../ros2.md) for topic checks and [launch](launch.md) for the full sequence.
