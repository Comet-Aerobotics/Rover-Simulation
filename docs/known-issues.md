# Known issues and validation status

## Open

- The repaired camera pose and added RGB publisher have passed structural checks only. Confirm the camera view, mount placement, image and camera-info messages, and cross-host delivery in Isaac Sim before treating the feed as working. The camera's physical calibration is not yet verified.
- Windows Isaac Sim ↔ WSL Docker DDS discovery and `/cmd_vel` delivery are not end-to-end verified. Existing topic and node presence does not prove it.
- Current cross-host probes saw no matching subscription using multicast or a static peer to the WSL host. Windows inbound firewall policy is `BlockInbound` and local rules are GPO-managed; this is a plausible discovery barrier, not a confirmed cause. No firewall settings were changed.
- The previous `aiaa_rover_dev` container had a stale, empty `/dev/input` bind mount and lacked Docker device access for the input character devices. Compose now grants read access to `js0` and `event0`; the supported launcher verifies both can be opened and recreates the container when safe.
- The Stadia Joy and teleop nodes are now running in `aiaa_rover_dev`; `joy_node` has `/dev/input/event0` open and `/joy` produced a Joy message. `/joy` and `/cmd_vel` each have a publisher. A nonzero stick sample has not yet been observed.
- The supported launcher now defaults Isaac Sim to its bundled Humble libraries to match Docker; the current process was relaunched with that setting. The live ROS graph still shows zero Isaac `/cmd_vel` subscribers. The graph needs playback ticks, so start the intended scene and recheck; the active stage has an unsaved marker and was left open.
- The legacy `cometbot_dev` container remains running and untouched; no Joy or teleop nodes were present in it during the current diagnostic.
- The canonical `scenes/CAMERASYNCSSMOETIMES.usd` composes the local VLP-16 Jackal, remaps all four wheel tokens, corrects DEM orientation, and adds colliders to the seven placed rocks. It opened and rendered in Isaac Sim 6.1 and was reviewed visually. Powered wheel motion, sustained contact stability, and sensor output correctness still need acceptance.
- The canonical Jackal base has no authored mass or density, so its mass is derived by the physics solver from collision geometry; its four wheels have explicit masses of 0.477 kg each. `scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd` assigns the base 53.092 kg, retaining a 55 kg total. Compare settling and bounce behavior in Isaac Sim before promoting it.
- Isaac Sim 6.1 automatically migrated deprecated ROS/physics graph node types in memory when opening the candidate. The window showed an unsaved marker and a PoseTree warning for `/jackal/base_link/laser`; the simulation was paused and the scene was not saved. Check the migration and warning on a clean reopen before saving the stage.
- The wall material's stale UI default referenced absent `BlackPaint2_BlackPaint_nor_dx_4k.exr`. Its project copy now points that default to the existing BlackPaint normal map already used by the active material and referenced by `BlackPaint.mdl`.
- Wheel-controller speed limit values appear stage-scaled; confirm units and motion behavior in Isaac before changing YAML.
- Older referenced USDC assets report crate version 0.7.0 deprecation warnings in `usd-core` 26.11. They opened for structural audit; verify the full scene with Isaac Sim's bundled USD before editing those layers.

## Verified observations

- Installed Isaac Sim reports 6.1.0 and bundles both Humble and Jazzy ROS libraries. Its `setup_ros_env.bat` defaults to Jazzy/Zenoh; the supported launcher explicitly selects Humble/Fast DDS/domain 0 to match Docker.
- `cometbot_dev` is running from the old source bind mount and remains untouched.
- GUI inspection confirmed the candidate stage and `/jackal/ActionGraph` are visible and the simulation can run. The `/cmd_vel` graph remains at zero because no command was delivered; a ROS TF aggregation warning also appeared during the interactive run.
- Stadia controller attached to WSL; `/dev/input/js0` and `event0` are visible in both WSL and the recreated `aiaa_rover_dev` container.
- Docker ROS has `/joy_node` and `/teleop_publisher`; current `/joy` and `/cmd_vel` publisher counts are 1 each. The `/cmd_vel` subscriber count is 0 from the Windows Isaac process.
- Canonical saved stage has Z up, 1 m/unit, terrain mesh with one static triangle-mesh collider and no terrain rigid body. `Cube_003` is inactive (not composed as simulation geometry).
- Saved graph has `/cmd_vel` subscriber and wheel joint tokens listed in [Action Graph doc](isaac/action-graph.md).
- USD-core 26.11 dependency scan: canonical stage has three unresolved items (SDK `OmniPBR.mdl`, anonymous Replicator sublayer, remote Jackal USD). The local-Jackal candidate has one unresolved item, `OmniPBR.mdl`, which is provided by the Isaac Sim runtime rather than this project.

“Verified observations” indicate local inventory/inspection, not full functional certification. The generated build outputs and USD-core tooling used for audits are preserved outside the active project in the adjacent source archive. See `docs/inventory.md` for source provenance and validation coverage.
