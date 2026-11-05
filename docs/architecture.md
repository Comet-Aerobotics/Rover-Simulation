# Architecture and ownership

```text
Stadia controller --USB/IP--> WSL /dev/input/js* --> Docker ROS Humble
  joy_node (/joy: sensor_msgs/Joy) --> teleop_publisher (/cmd_vel: geometry_msgs/Twist)
  --> DDS/Fast DDS over WSL host network --> Isaac Sim 6.1 on Windows
  --> USD Action Graph --> Jackal differential articulation in LunaLab
```

Isaac Sim owns the canonical USD stage and `/jackal/ActionGraph`; ROS owns Joy-to-Twist mapping. YAML records shared intent and the values that require parity checks. No independently generated Action Graph is maintained. Terrain source rasters live under `assets/terrain/source`; processed outputs are reproducible artifacts. Third-party or separately licensed robot assets are tracked as external dependencies when redistribution rights are unclear.

`legacy/archived_scripts/` preserves only original scripts/configs that directly informed this simulation. Full repository snapshots, Git metadata, the broad OmniLRS checkout, the optional MCP repository, and unvalidated scene alternatives are in the adjacent `AIAA-Isaac-Sim-Rover-source-archive/`; they are not runtime dependencies. `work/` is scratch and excluded from version control.

## Observed system

Windows 11 + Isaac Sim 6.1.0 (local install); WSL Ubuntu; Docker in WSL; ROS 2 Humble, `rmw_fastrtps_cpp`, domain 0; Stadia rev A via usbipd-win. Existing container `cometbot_dev` mounts the old `microros-dockercompose/CAN` folder at `/root/CAN`; its package source remains there until the new package is built and checked in the new tree. The new Compose project deliberately uses `aiaa_rover_dev` to avoid replacing the old container.

See [ROS flow](ros2.md), [Windows setup](setup/windows.md), and [WSL/Docker setup](setup/wsl-docker.md).
