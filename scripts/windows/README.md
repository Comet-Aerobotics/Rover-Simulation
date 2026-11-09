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

`start_rover.ps1 -Mode Start` lists joystick devices visible in WSL. It selects the only detected controller automatically, or prompts for a numbered selection when several are connected. Choose one device to use one gamepad, or enter two device numbers (for example, `1,2`) to combine a split-controller pair: the first device vertical axis drives forward/reverse and the second device horizontal axis steers. The selected input device(s) are used by `joy_node` and the teleop node.

For a controller connected to another Windows computer, install usbipd-win there and run `usbipd bind --busid <BUSID>` in an elevated PowerShell window for the controller device(s). The launcher discovers USB/IP devices on online Tailscale peers, prompts when there are multiple choices, and remembers selections in the simulation computer's ignored `.env`. It attaches the remote devices into WSL and selects from the joystick devices WSL exposes. See the [remote controller setup guide](../../docs/setup/remote-controller.md) for Windows sharing, firewall, WSL client and HID driver setup, and Joy-Con 2 pair selection. Remote attach is per session/device connection, while `usbipd bind` on the source computer persists.
