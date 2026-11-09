# ROS 2 container runtime

`docker/compose.yaml` defines the WSL-hosted `aiaa_rover_dev` service. It builds from the Humble `Dockerfile`, bind-mounts the ROS workspace and shared YAML configuration, makes `/dev/input` available with character-device read permission, and uses host networking for DDS. `fastdds.xml` is the reviewed profile; it has no fixed historical initial peer.

| Setting | Current design | Why it matters |
| --- | --- | --- |
| Network | `network_mode: host` inside WSL | ROS discovery uses the WSL host network, not a private Compose bridge |
| ROS domain | `${ROS_DOMAIN_ID:-0}` | Must match the Isaac Sim process environment |
| Middleware | `rmw_fastrtps_cpp` | Matches the supported Isaac launch |
| Joystick | `/dev/input` bind mount and `c 13:* r` device cgroup rule in the current working Compose file | Launcher chooses one or two WSL-visible `jsN` devices and checks container access; device IDs go to ROS launch |
| Config mount | `../config:/opt/rover/config:ro` | Teleop launch reads Joy and controller YAML |
| Workspace mount | `../ros2/cometbot_ws:/workspace` | Container builds the Humble package at startup |

The Windows launcher uses Docker **inside WSL**; the Windows CLI may select another Docker context. `cometbot_dev` is a separate legacy container and must not run duplicate Joy/teleop nodes on the same domain. See [WSL/Docker setup](../docs/setup/wsl-docker.md), [ROS flow](../docs/ros2.md), and [launch](../docs/setup/launch.md).
