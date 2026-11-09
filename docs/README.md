# Simulation documentation

Start at the [root README](../README.md) for launch commands and scene selection. Use these guides for the details of each subsystem:

| Guide | Questions it answers |
| --- | --- |
| [Architecture](architecture.md) | Which process or file owns each part of the simulation? |
| [Rover](rover.md) | Which body, joints, colliders, masses, and drive parameters move the vehicle? |
| [Terrain](terrain.md) | How are DEM heights, static collision, and live sand ruts produced and checked? |
| [Environment](environment.md) | Which LunaLab structures, rocks, lights, and materials affect the scene? |
| [Sensors](sensors.md) | What camera, lidar, TF, and clock outputs exist and how can they be checked? |
| [ROS 2](ros2.md) | How does joystick input become a wheel command, and what are the topics? |
| [Action Graphs](isaac/action-graph.md) | Which graph in the USD owns each command or sensor path? |
| [Launch](setup/launch.md) | How do you start, select a scene, diagnose, and stop the stack? |
| [Remote controller](setup/remote-controller.md) | How do you share a controller over Tailscale/USB-IP and select a split pair? |
| [Troubleshooting](troubleshooting.md) | What should be checked when a visible or ROS behavior fails? |
| [Performance](performance-analysis.md) | Which costs were measured, under what conditions, and what remains to test? |
| [Known issues](known-issues.md) | Which findings are confirmed, provisional, or awaiting GUI acceptance? |

The [inventory](inventory.md), [migration notes](migration.md), and [source manifest](source-manifest.md) record provenance and earlier snapshots. Their dated observations should not override the current code, saved USD, or a fresh runtime check. Paths and parameter values in the subsystem guides were checked against this repository's current source and scene composition; a modified working scene can differ from the tracked canonical USD.
