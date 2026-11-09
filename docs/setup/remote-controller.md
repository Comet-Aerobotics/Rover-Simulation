# Remote controllers over Tailscale

Use this guide when the rover simulation runs on one Windows computer and the controller is plugged into a different Windows 11 computer. USB/IP forwards the physical USB devices through Tailscale to Ubuntu on the simulation computer, where ROS reads them. Windows on the controller computer does not send gamepad events through Remote Desktop itself.

## Requirements

- Both Windows computers are online in the same Tailscale network.
- The simulation computer has the repository launcher, Ubuntu WSL 2, and Docker set up.
- The controller computer can share USB devices with `usbipd-win`.
- The simulation computer can reach the controller computer's USB/IP service on TCP port 3240 over Tailscale. Restrict any added firewall rule to the simulation computer's Tailscale IP.

## Share the controller from Windows 11

On the computer where the controller is physically plugged in, install `usbipd-win` from an Administrator PowerShell window:

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

Then list USB devices in Administrator PowerShell:

```powershell
usbipd list
```

For each controller device that should be shared, use its current BUSID:

```powershell
usbipd bind --busid <BUSID>
```

Run `usbipd list` again and confirm each controller says `Shared`. `bind` makes the device available to USB/IP; it does not attach it to the simulation computer. The launcher attaches it when starting the rover. While attached to WSL on the simulation computer, the USB device is unavailable to Windows on the controller computer. A binding persists, but the remote computer and Tailscale connection must be online whenever the rover is started.

### If USB/IP reports `Device busy (exported)`

This means Windows or software on the controller computer still holds the device. From **Administrator PowerShell on the controller computer**, force usbipd-win to claim each controller, replacing the Windows driver binding:

```powershell
usbipd bind --force --busid <LEFT_BUSID>
usbipd bind --force --busid <RIGHT_BUSID>
usbipd list
```

Use the BUSIDs currently shown by `usbipd list`; they can change after reconnecting devices. Confirm both are `Shared`, then retry the rover launcher. A reboot may be needed after a forced bind. This claim prevents Windows from using those controllers until they are unbound. See the [usbipd-win maintainer's explanation](https://github.com/dorssel/usbipd-win/issues/304) of this error.

If the launcher cannot discover the controller computer, check that TCP 3240 is reachable over Tailscale. The default Windows firewall rule may not include the Tailscale address range. Add a narrowly scoped inbound rule from an elevated PowerShell prompt on the controller computer, substituting the simulation computer's Tailscale IPv4 address:

```powershell
New-NetFirewallRule `
  -DisplayName 'usbipd from rover simulation over Tailscale' `
  -Direction Inbound -Protocol TCP -LocalPort 3240 `
  -RemoteAddress <SIM_TAILSCALE_IP> -Action Allow
```

## Start the rover from the simulation computer

The first time, install the USB/IP client in Ubuntu WSL if it is not already installed:

```bash
sudo apt update
sudo apt install linux-tools-virtual hwdata
command -v usbip
```

If `command -v usbip` prints no path, follow the [usbipd-win WSL support instructions](https://github.com/dorssel/usbipd-win/wiki/WSL-support) to make the matching USB/IP client available in WSL. This is the Linux USB/IP client; it is separate from `usbipd-win` on the controller computer.

Start the usual launcher from the repository root on the simulation computer:

```powershell
.\scripts\windows\start_rover_all.ps1
```

In Start mode, the launcher scans online Tailscale peers for shared USB/IP devices. It automatically uses a single available host; if more than one computer is sharing devices, it asks which computer to use. It asks which devices to attach when the device names are generic or there are multiple choices. The selection is saved in the simulation computer's ignored `.env` file, so users do not have to commit or manually maintain per-person hostnames and BUSIDs. If a device or BUSID changes, the launcher prompts again. `.env` values for a preferred host or BUSIDs are optional overrides.

Confirm that the launch output lists the controller under **Controllers visible to WSL** as `/dev/input/jsN`. The input monitor should then show changing `sensor_msgs/msg/Joy` values when sticks or buttons move. If USB devices appear in `usbip list` but no joystick node appears in WSL, Linux may not have a HID driver for that controller; see the driver section below.

## Controller drivers

USB/IP forwards the USB device. It does not provide a Linux HID driver. Install/configure USB/IP on the Windows controller computer, but install a needed Linux HID driver in Ubuntu WSL on the simulation computer. Most common gamepads use HID drivers already included in the Linux kernel and need no extra driver. Check `/dev/input/jsN` first; if it appears and its Joy values change, no extra driver is needed.

### Nintendo Switch 2 Joy-Cons over USB

The Switch 2 Joy-Con 2 USB devices may require the community [`hid-nintendo2-dkms` Linux driver](https://github.com/XenuIsWatching/hid-nintendo2-dkms). It supports the Joy-Con 2 left (`057e:2067`) and right (`057e:2066`) over USB. It is not a Windows driver and does not cover Bluetooth input. The driver project requires kernel headers matching the running Linux kernel, `make`, a compatible C compiler, and DKMS for its DKMS installation.

First check WSL's running kernel and whether matching build files are installed:

```bash
uname -r
test -e "/lib/modules/$(uname -r)/build" && echo 'matching kernel build files found' || echo 'matching kernel build files missing'
```

On a Linux system with matching headers, the driver's documented DKMS installation is:

```bash
sudo apt install build-essential dkms git
git clone https://github.com/XenuIsWatching/hid-nintendo2-dkms.git
cd hid-nintendo2-dkms
sudo cp -r . /usr/src/hid-nintendo2-0.1.0
sudo dkms add -m hid-nintendo2 -v 0.1.0
sudo dkms build -m hid-nintendo2 -v 0.1.0
sudo dkms install -m hid-nintendo2 -v 0.1.0
```

**WSL kernel caveat:** Do not install generic Ubuntu kernel headers as a substitute for headers matching `uname -r`. WSL uses a Microsoft kernel, and a module built for a different kernel will not load. If the matching build files are missing, compiling/loading this driver requires a WSL kernel/module setup that matches the running kernel; see Microsoft's [WSL2 kernel build instructions](https://github.com/microsoft/WSL2-Linux-Kernel#build-instructions) and [custom kernel configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config). This is a kernel-level change used by WSL distributions on that computer. After a compatible module is installed, reconnect the Joy-Cons and verify the driver and joystick nodes before launching ROS.

If matching WSL headers are unavailable, stop at the check above rather than running the DKMS commands against arbitrary Ubuntu headers. The Joy-Con driver is only needed if the devices are visible over USB/IP but do not become usable Linux input devices.

## Joy-Con 2 pair behavior

When attached through a charging grip, the left and right Joy-Con 2 enumerate as **two USB devices and two joystick devices**. That is expected; USB/IP and Linux do not turn them into one physical controller. The rover launcher can use them as a split-controller pair and combine their axes into one `/cmd_vel` command.

At the remote USB device prompt, select both Joy-Cons. Select the left Joy-Con first, then the right. For example, if the prompt lists right (`057e:2066`) as item 1 and left (`057e:2067`) as item 2, enter:

```text
2,1
```

At the later joystick prompt, choose the left Joy-Con's displayed joystick number first and the right Joy-Con's number second. If a local gamepad is also attached, it will appear as another choice; choose the two entries named for the Joy-Cons. The pair mapping uses the **left stick's vertical axis** for forward/reverse and the **right stick's horizontal axis** for turning. Buttons are not combined into a single Joy message by this mapping.

The launcher remembers the selected USB IDs locally. If the joystick list order changes, use the displayed controller names to reselect left then right. The monitor may show `/joy_left` and `/joy_right` separately even though teleop combines them to drive the rover.

## Troubleshooting order

1. On the controller computer, confirm `usbipd list` reports the intended devices as `Shared`.
2. On the simulation computer, confirm the Tailscale peer is online and TCP 3240 is reachable. If discovery fails, check the controller computer's scoped firewall rule.
3. Confirm launcher output lists the exported remote USB devices and then `/dev/input/jsN` devices in WSL.
4. Move each stick and confirm its Joy monitor values change. If USB is visible but no joystick node appears, check Linux HID driver support, especially the WSL matching-kernel-header requirement for Joy-Con 2.
5. Confirm Docker can read the selected joystick and the ROS Joy monitor changes. For a split Joy-Con pair, verify both `/joy_left` and `/joy_right`, then check `/cmd_vel`.

See [Windows host setup](windows.md), [launch details](launch.md), and the [troubleshooting table](../troubleshooting.md) for the rest of the ROS/Isaac path.
