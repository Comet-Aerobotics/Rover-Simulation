# Known issues and validation status

## Open

- Windows Isaac Sim ↔ WSL Docker DDS discovery and `/cmd_vel` delivery are not end-to-end verified. Existing topic and node presence does not prove it.
- Current cross-host probes saw no matching subscription using multicast or a static peer to the WSL host. Windows inbound firewall policy is `BlockInbound` and local rules are GPO-managed; this is a plausible discovery barrier, not a confirmed cause. No firewall settings were changed.
- USB attachment and idle Joy were observed, but nonzero Stadia input mapping is not validated.
- The existing `cometbot_dev` still runs the old Joy/teleop nodes. The new image/container is available, but the consolidated teleop launch was deliberately not started until the legacy nodes are intentionally stopped; no cutover was performed.
- The preserved baseline `scenes/CAMERASYNCSSMOETIMES.usd` still references NVIDIA's remote Isaac 5.0 Jackal layer. The default `scenes/CAMERASYNCSSMOETIMES_LOCAL_JACKAL_CANDIDATE.usd` composes the local VLP-16 Jackal, remaps all four wheel tokens, and removes the anonymous Replicator sublayer and empty configuration payloads. It opened and rendered in Isaac Sim 6.1; four wheel DOFs were present and a runtime contact sensor observed a wheel-terrain contact. Powered wheel motion, sustained contact stability, and sensor output correctness still need acceptance.
- Isaac Sim 6.1 automatically migrated deprecated ROS/physics graph node types in memory when opening the candidate. The window showed an unsaved marker and a PoseTree warning for `/jackal/base_link/laser`; the simulation was paused and the scene was not saved. Check the migration and warning on a clean reopen before saving the stage.
- The wall material's stale UI default referenced absent `BlackPaint2_BlackPaint_nor_dx_4k.exr`. Its project copy now points that default to the existing BlackPaint normal map already used by the active material and referenced by `BlackPaint.mdl`.
- Wheel-controller speed limit values appear stage-scaled; confirm units and motion behavior in Isaac before changing YAML.
- Older referenced USDC assets report crate version 0.7.0 deprecation warnings in `usd-core` 26.11. They opened for structural audit; verify the full scene with Isaac Sim's bundled USD before editing those layers.

## Verified observations

- Installed Isaac Sim reports 6.1.0; its `setup_ros_env.bat` defaults to Jazzy/Zenoh but preserves an explicit `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`. Docker reports ROS Humble/Fast DDS, domain 0.
- `cometbot_dev` is running from the old source bind mount and remains untouched.
- GUI inspection confirmed the candidate stage and `/jackal/ActionGraph` are visible and the simulation can run. The `/cmd_vel` graph remains at zero because no command was delivered; a ROS TF aggregation warning also appeared during the interactive run.
- Stadia controller attached to WSL; `/dev/input/js0` and `event0` visible; ROS lists the controller.
- Docker ROS exposes `/joy`, `/cmd_vel`, `/joy_node`, `/teleop_publisher`; sampled messages were idle/zero.
- Canonical saved stage has Z up, 1 m/unit, terrain mesh with one static triangle-mesh collider and no terrain rigid body. `Cube_003` is inactive (not composed as simulation geometry).
- Saved graph has `/cmd_vel` subscriber and wheel joint tokens listed in [Action Graph doc](isaac/action-graph.md).
- USD-core 26.11 dependency scan: canonical stage has three unresolved items (SDK `OmniPBR.mdl`, anonymous Replicator sublayer, remote Jackal USD). The local-Jackal candidate has one unresolved item, `OmniPBR.mdl`, which is provided by the Isaac Sim runtime rather than this project.

“Verified observations” indicate local inventory/inspection, not full functional certification. The generated build outputs and USD-core tooling used for audits are preserved outside the active project in the adjacent source archive. See `docs/inventory.md` for source provenance and validation coverage.
