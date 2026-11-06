# Troubleshooting

- **No joystick in WSL:** check `usbipd list`, attach the correct BUSID to the intended distro, then verify `/dev/input/js*` and `joy_enumerate_devices`.
- **Joystick in WSL, missing in Docker:** inspect container device mappings and input group permissions. Restarting the old `cometbot_dev` is not part of the new startup script.
- **Duplicate ROS nodes:** inspect `ros2 node list` before launching. The launcher refuses to spawn a duplicate in the selected container.
- **`/cmd_vel` exists but Isaac does not move:** topic existence is not discovery. Check Isaac Bridge loaded, Fast DDS on both ends, domain ID, DDS participant logs, interfaces/firewall, and subscriber count. Test with safe nonzero input only after immobilizing the rover.
- **Discovery regression:** remove historical peer `10.255.255.254` and stale profile environment variables, then re-check network interfaces. No default peer is configured here.
- **Windows/WSL discovery:** an earlier probe found no Isaac subscriber, but the current running scene exposes two Isaac `/cmd_vel` subscribers to WSL, and scan, image, camera-info, and TF messages have reached WSL. Recheck the live graph during playback before treating an old zero-subscriber snapshot as a firewall problem.
- **Lidar rays or points missing in the viewport:** the shared PhysX lidar USD now has `drawLines` and `drawPoints` enabled. Save any unrelated in-memory stage edits, then reload the scene to pick up the asset change. This display setting is separate from `/scan` publication.
- **Terrain float/jitter:** verify exactly one static triangle-mesh collider at `/Lunalab/Terrain/terrain_mesh`, approximation `none`, no terrain rigid body. Do not add a convex hull.
- **Missing USD assets:** external references and licensing are listed in `docs/known-issues.md`. Built-in `OmniPBR.mdl` resolves from the Isaac Sim runtime. The canonical scene uses the copied VLP-16 asset. The stale BlackPaint UI default has been repaired in the project-local wall layer.
- **Scene UI differs from file:** Isaac Sim 6.1 may automatically migrate deprecated graph nodes in memory. Review those changes before saving the canonical scene.
