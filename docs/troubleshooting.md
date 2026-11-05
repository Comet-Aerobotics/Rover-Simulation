# Troubleshooting

- **No joystick in WSL:** check `usbipd list`, attach the correct BUSID to the intended distro, then verify `/dev/input/js*` and `joy_enumerate_devices`.
- **Joystick in WSL, missing in Docker:** inspect container device mappings and input group permissions. Restarting the old `cometbot_dev` is not part of the new startup script.
- **Duplicate ROS nodes:** inspect `ros2 node list` before launching. The launcher refuses to spawn a duplicate in the selected container.
- **`/cmd_vel` exists but Isaac does not move:** topic existence is not discovery. Check Isaac Bridge loaded, Fast DDS on both ends, domain ID, DDS participant logs, interfaces/firewall, and subscriber count. Test with safe nonzero input only after immobilizing the rover.
- **Discovery regression:** remove historical peer `10.255.255.254` and stale profile environment variables, then re-check network interfaces. No default peer is configured here.
- **Current Windows/WSL discovery probe:** multicast and a static peer to the WSL host did not find a matching Isaac subscriber. Inbound firewall policy is block-by-default and local firewall rules are GPO-managed; this may explain the result, but it has not been established as the cause. Do not add firewall rules without administrator review.
- **Terrain float/jitter:** verify exactly one static triangle-mesh collider at `/Lunalab/Terrain/terrain_mesh`, approximation `none`, no terrain rigid body. Do not add a convex hull.
- **Missing USD assets:** external references and licensing are listed in `docs/known-issues.md`. Built-in `OmniPBR.mdl` resolves from the Isaac Sim runtime. The default local-Jackal scene uses the copied VLP-16 asset; the preserved baseline still has a remote Jackal payload. The stale BlackPaint UI default has been repaired in the project-local wall layer.
- **Scene UI differs from file:** Isaac Sim 6.1 automatically migrated deprecated graph nodes in memory when the candidate was opened. That stage showed an unsaved marker and was not saved. Reopen the selected scene to compare the saved file before applying or saving graph migrations.
