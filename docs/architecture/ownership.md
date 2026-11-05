# File ownership

- Stage, robot articulation, sensors, and OmniGraph: canonical local-Jackal USD at `scenes/CAMERASYNCSSMOETIMES.usd`; earlier scene snapshots are preserved in the adjacent source archive.
- Shared robot and terrain settings: `config/simulation.yaml`; Joy/Twist parameters: `config/controller.yaml`; middleware/domain: `config/ros.yaml`.
- ROS runtime code: `ros2/cometbot_ws/src/cometbot_control`; no application code is loaded from `legacy/`.
- Terrain generation/repair/audit: `terrain/`; validators do not launch simulation or send ROS commands.
- Container and DDS settings: `docker/`; no fixed DDS initial peer.
- Host setup and diagnostics: `scripts/`.
- Selected original scripts: `legacy/archived_scripts/`; full broad intake and Git state: adjacent `AIAA-Isaac-Sim-Rover-source-archive/`; scratch tools: ignored `work/`.

When a USD-owned property is mirrored in YAML, the USD remains runtime authority and docs identify the parity check. Never generate a second Action Graph that can drift from the stage.
