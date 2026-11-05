# Windows host setup

1. Install Isaac Sim 6.1.0 and note its install root. The observed root is `C:\isaac-sim\_build\windows-x86_64\release`; set `ISAAC_SIM_ROOT` or edit `.env`.
2. Install WSL 2, Ubuntu, Docker in that distro or Docker Desktop's WSL integration, and usbipd-win. The observed host Docker CLI context is `desktop-linux`, which cannot see the rover container. The supported launcher deliberately calls Docker inside the selected WSL distro, where the observed context is `default`.
3. Connect the Stadia controller. `scripts/windows/start_rover.ps1` detects a unique Stadia/Google controller BUSID and attaches it only when not already attached. It avoids auto-attaching if multiple matches appear.
4. Isaac Sim 6.1's `setup_ros_env.bat` defaults to Jazzy/Zenoh. The supported launch sets `ROS_DISTRO=jazzy`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_DOMAIN_ID=0`, and clears stale DDS profile overrides before launching Isaac. Confirm the ROS 2 Bridge extension loads successfully before expecting discovery.
5. Run `scripts/windows/start_rover.ps1 -Mode Diagnostics`. If legacy teleop nodes are active in `cometbot_dev`, stop only their processes with `scripts/windows/stop_rover.ps1 -Container cometbot_dev`, verify they exit, then run `scripts/windows/start_rover.ps1 -Mode Start`.

Start mode opens WSL and ROS terminals, builds/starts the separate `aiaa_rover_dev`, runs node/topic checks, and launches the selected local-Jackal scene if Isaac Sim is not already open. The original baseline USD is preserved. The script never closes the legacy container or saves/terminates an already-open Isaac stage.

Cross-host DDS discovery is not yet validated. Avoid changing firewall, router, or multicast settings based only on the existing topic list; capture diagnostics first. See [troubleshooting](../troubleshooting.md).
