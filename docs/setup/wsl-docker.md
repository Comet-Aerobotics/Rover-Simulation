# WSL and Docker setup

The observed ROS container is `cometbot_dev`, ROS Humble with Fast DDS, `ROS_DOMAIN_ID=0`, and host networking in WSL. It currently bind-mounts the legacy `CAN` tree at `/root/CAN`; this container remains intact. The consolidated package is in `ros2/cometbot_ws` and Compose builds a separate `aiaa_rover_dev` container from it.

The Docker CLI in Windows currently points to `desktop-linux` and does not see `cometbot_dev`. Use Docker inside Ubuntu WSL. The supported Windows launcher handles this automatically. For manual commands, map the repo to its `/mnt/<drive>/...` path inside the selected distro, then use `docker compose -f docker/compose.yaml ...` there.

USB controller visibility: `usbipd list` on Windows should show the Stadia device attached to the selected distro; inside WSL inspect `/dev/input/js*` and `/dev/input/event*`. Device visibility in WSL does not guarantee it is mapped into a container. Compose bind-mounts `/dev/input` read-only for Joy input and adds the `input` group.

Start mode builds the new image/container only after checking that legacy `/joy_node` and `/teleop_publisher` are no longer active. Then it launches `ros2 launch cometbot_control teleop.launch.py`, which starts `joy_node` and `teleop_publisher`. Inspect with `ros2 node list`, `ros2 topic info /joy`, and `ros2 topic info /cmd_vel`. Do not run a second joystick or teleop node on domain 0 while the legacy stack is active.

The default Fast DDS profile has no hard-coded initial peer. Do not use the historical `10.255.255.254` peer. For Windows-to-WSL discovery, diagnose interface addresses, firewall, ROS domain, middleware, and bridge logs together; see [ROS 2](../ros2.md).
