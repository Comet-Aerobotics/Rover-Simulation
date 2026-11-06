# scripts/windows/

Windows launch orchestration for Isaac Sim and WSL/Docker, including diagnostics, combined startup, compatibility entry point, and controlled shutdown.

## Contents

- start_isaac_sim.ps1
- start_rover_all.ps1
- start_rover.ps1
- stop_rover.ps1

## Simulation relevance
These helpers make startup and diagnostics repeatable across the Windows host and WSL runtime.

## Controller selection

`start_rover.ps1 -Mode Start` lists joystick devices visible in WSL. It selects the only detected controller automatically, or prompts for a numbered selection when several are connected. The selected `/dev/input/jsN` is passed through to the ROS container and used as the `joy_node` device ID.

For a controller connected to another computer, first share it from that computer with a USB-over-IP server and attach it to this computer's WSL distro. The launcher detects it after WSL exposes it under `/dev/input/jsN`; it does not establish the USB-over-IP connection itself. With `usbipd-win` on the controller computer, run `usbipd list` and `usbipd bind --busid <BUSID>` in an elevated PowerShell window, then allow the sim computer to reach TCP port 3240 over Tailscale. From the sim computer's WSL distro, list and attach the shared controller with `usbip list --remote=<controller-computer-tailnet-name>` and `sudo usbip attach --remote=<controller-computer-tailnet-name> --busid=<BUSID>`. Then run the launcher. Restrict the USB/IP firewall rule to the intended Tailscale peer.
