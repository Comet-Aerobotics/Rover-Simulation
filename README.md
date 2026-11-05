# AIAA Isaac Sim Rover

Consolidated workspace for the AIAA rover simulation: Isaac Sim 6.1.0, LunaLab, Jackal articulation, ROS 2 Humble teleoperation in WSL/Docker, and the Windows/WSL bridge.

## Start here

1. Review [the inventory](docs/inventory.md), [known issues](docs/known-issues.md), and [migration notes](docs/migration.md). Originals and source snapshots are retained.
2. Install/configure Windows, WSL 2, Docker Desktop's WSL engine, usbipd-win, and Isaac Sim 6.1.0 per [Windows setup](docs/setup/windows.md) and [WSL/Docker setup](docs/setup/wsl-docker.md).
3. Copy `.env.example` to `.env`, set local paths, and review `config/*.yaml`.
4. Run `scripts/windows/start_rover.ps1 -Mode Diagnostics` first. If the old `cometbot_dev` teleop nodes are active, stop only that launch with `scripts/windows/stop_rover.ps1 -Container cometbot_dev`, verify node exit, then run `scripts/windows/start_rover.ps1 -Mode Start`. For Isaac-only startup, use `scripts/windows/start_isaac_sim.ps1`.
5. The launcher builds/starts the separate `aiaa_rover_dev`, opens ROS teleop and `/joy` terminals, then launches the selected local-Jackal scene unless Isaac Sim is already open. The original `CAMERASYNCSSMOETIMES.usd` stays preserved as the baseline and is not the default because it references NVIDIA's remote Jackal layer. Confirm the ROS 2 Bridge and DDS discovery before testing motion.

The local-Jackal scene has opened and rendered in Isaac Sim 6.1; its rover articulation exposes four wheel DOFs, and a runtime contact sensor observed a front wheel on the terrain. Powered motion and contact stability are not yet validated. The complete teleop path is also **not yet certified end-to-end**: Windows Isaac Sim ↔ WSL Docker discovery and nonzero command delivery remain open. Do not infer success from topic existence alone.

## Owners

- `scenes/`: selected local-Jackal stage and preserved baseline; the USD owns its OmniGraph Action Graph.
- `config/`: shared human-readable parameters; values mirrored in USD are documented as parity checks.
- `assets/`: simulation models, environment dependency closure, terrain sources, and materials.
- `isaac/`: Isaac Sim inspection/validation scripts and extensions.
- `terrain/`: offline terrain tools.
- `ros2/`: ROS package and launch files.
- `docker/`, `scripts/`: container and host lifecycle tooling.
- `legacy/archived_scripts/`: selected original scripts/configs retained for provenance. Full initial intake copies are outside this focused tree at `../AIAA-Isaac-Sim-Rover-source-archive/`.

See the [simulation ownership audit](docs/ownership-and-migration.md), [launch guide](docs/setup/launch.md), [architecture](docs/architecture.md), [Action Graph](docs/isaac/action-graph.md), [terrain](docs/terrain.md), [ROS 2](docs/ros2.md), and [verification map](tests/README.md).
