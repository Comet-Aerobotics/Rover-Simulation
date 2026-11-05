# AIAA / UTD Rover launcher - Windows PowerShell 5.1 compatible.
# Run as Administrator for first-time USB bind/attach.
[CmdletBinding()]
param(
    [string]$BusId = '',
    [string]$Distro = 'Ubuntu',
    [string]$ContainerName = 'cometbot_dev',
    [string]$Workspace = '/root/CAN/cometbot_ws',
    [switch]$SkipUSB,
    [switch]$SkipIsaac,
    [switch]$WithAI,
    [switch]$NoJoyMonitor,
    [switch]$NoShellWindows,
    [switch]$NoAutoDockerDesktop
)
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stackScript = Join-Path $scriptDir 'start_stack_fixed.ps1'
function Say([string]$s) { Write-Host "[ROVER] $s" -ForegroundColor Cyan }
function Warn([string]$s) { Write-Warning "[ROVER] $s" }
function Quote-Sh([string]$s) { return "'" + $s.Replace("'", "'\''") + "'" }
function Is-Admin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Invoke-Wsl([string]$script, [switch]$AllowFailure) {
    & wsl.exe -d $Distro -- bash -lc $script
    $code = $LASTEXITCODE
    if (($code -ne 0) -and (-not $AllowFailure)) { throw "WSL command failed ($code): $script" }
    return $code
}
function Start-ShellWindow([string]$title, [string]$wslScript) {
    # Base64 prevents parsing confusion between Windows PowerShell, WSL and bash.
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($wslScript))
    $child = @'
$Host.UI.RawUI.WindowTitle = 'TITLE_HERE'
Write-Host 'TITLE_HERE' -ForegroundColor Cyan
$cmd = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('B64_HERE'))
& wsl.exe -d 'DISTRO_HERE' -- bash -lc $cmd
Write-Host ''
Write-Host 'Session ended. Check the output above.' -ForegroundColor Yellow
'@
    $child = $child.Replace('TITLE_HERE', $title).Replace('B64_HERE', $b64).Replace('DISTRO_HERE', $Distro)
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoLogo', '-NoProfile', '-NoExit', '-EncodedCommand', $encoded) | Out-Null
}

Say "Starting / waking WSL distribution '$Distro'..."
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'WSL is not installed.' }
$distros = (& wsl.exe --list --quiet | Out-String)
# --list may use UTF-16 formatting on Windows: normalize embedded NULs.
$distros = $distros -replace '\x00', ''
if ($distros -notmatch [regex]::Escape($Distro)) { throw "WSL distro '$Distro' not found. Run: wsl --list --verbose" }
# This intentionally starts WSL before usbipd attach and before docker checks.
Invoke-Wsl 'echo WSL_READY' | Out-Null
Say 'WSL ready.'

Say 'Checking Docker engine inside WSL...'
$dockerReady = $false
for ($i=0; $i -lt 8; $i++) {
    & wsl.exe -d $Distro -- bash -lc 'docker info >/dev/null 2>&1'
    if ($LASTEXITCODE -eq 0) { $dockerReady = $true; break }
    if ($i -eq 0 -and -not $NoAutoDockerDesktop) {
        $desktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
        if (Test-Path $desktop) { Say 'Opening Docker Desktop...'; Start-Process -FilePath $desktop | Out-Null }
    }
    Start-Sleep -Seconds 3
}
if (-not $dockerReady) { throw 'Docker engine unavailable inside Ubuntu. Open Docker Desktop, enable WSL integration for Ubuntu, and rerun.' }
Say 'Docker engine ready.'

if (-not $SkipUSB) {
    if (-not (Get-Command usbipd.exe -ErrorAction SilentlyContinue)) { throw 'usbipd-win is not installed.' }
    $devices = (& usbipd.exe list | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'usbipd list failed.' }
    if (-not $BusId) {
        $line = $devices -split "`r?`n" | Where-Object { $_ -match 'Stadia Controller' } | Select-Object -First 1
        if (-not $line -or $line -notmatch '^\s*(\d+-\d+)\s+') { throw 'Stadia Controller not listed by usbipd. Check cable and USB port.' }
        $BusId = $Matches[1]
    }
    $line = $devices -split "`r?`n" | Where-Object { $_ -match ('^\s*' + [regex]::Escape($BusId) + '\s+') } | Select-Object -First 1
    if (-not $line) { throw "BUSID $BusId was not found." }
    Say "Stadia: $line"
    if ($line -notmatch '\bAttached\b') {
        if (-not (Is-Admin)) { throw 'Run PowerShell as Administrator to attach the USB controller.' }
        if ($line -match '\bNot shared\b') {
            & usbipd.exe bind --busid $BusId
            if ($LASTEXITCODE -ne 0) { throw 'usbipd bind failed.' }
        }
        & usbipd.exe attach --wsl --busid $BusId
        if ($LASTEXITCODE -ne 0) { throw 'usbipd attach failed.' }
    }
    # The Linux HID/input driver may take a moment to make nodes visible.
    $found = $false
    for ($i=0; $i -lt 10; $i++) {
        & wsl.exe -d $Distro -- bash -lc 'test -e /dev/input/js0 || test -e /dev/input/event0'
        if ($LASTEXITCODE -eq 0) { $found = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $found) { throw 'Controller attached but no WSL input device appeared. In Ubuntu check lsusb and ls /dev/input.' }
    Say 'WSL controller input device found.'
}

$cn = Quote-Sh $ContainerName
$exists = (& wsl.exe -d $Distro -- bash -lc "docker container inspect $cn --format '{{.State.Running}}' 2>/dev/null" | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "Container '$ContainerName' is missing. Start/create it using the TEAM Docker Compose file (do not use the old microros container)." }
if ($exists -ne 'true') { Say "Starting stopped container $ContainerName..."; Invoke-Wsl "docker start $cn >/dev/null" | Out-Null }
Say "Container $ContainerName running."
$deviceCheck = "docker exec $cn sh -c 'test -e /dev/input/js0 || test -e /dev/input/event0'"
& wsl.exe -d $Distro -- bash -lc $deviceCheck
if ($LASTEXITCODE -ne 0) { throw 'Controller is missing inside Docker. Check the Compose device mounts, then recreate the container with the original Compose file.' }

# Prevent the previously broken discovery XML peer override from being inherited by newly spawned nodes.
$setup = "unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE; source $(Quote-Sh "$Workspace/install/setup.bash")"
$checks = "$setup && command -v ros2 >/dev/null && ros2 pkg executables joy | grep -q joy_node && ros2 pkg executables cometbot_control | grep -q teleop_publisher"
Invoke-Wsl "docker exec $cn bash -lc $(Quote-Sh $checks)" | Out-Null
Say 'ROS 2 workspace and executables available.'

if (-not $SkipIsaac) {
    if (-not (Test-Path -LiteralPath $stackScript)) { throw "Missing companion script beside this file: $stackScript" }
    Say 'Starting Isaac Sim with Fast DDS configuration...'
    & $stackScript -SkipAI:(!$WithAI)
}

# pgrep is used only to avoid duplicates; verify nodes via ROS 2 after starting.
foreach ($entry in @(@('joy_node','joy','joy_node'), @('teleop_publisher','cometbot_control','teleop_publisher'))) {
    $process = $entry[0]; $pkg = $entry[1]; $exe = $entry[2]
    $nodeName = "/$process"
    $probeScript = "$setup && ros2 node list --no-daemon | grep -Fxq $(Quote-Sh $nodeName)"
    $probe = "docker exec $cn bash -lc $(Quote-Sh $probeScript)"
    & wsl.exe -d $Distro -- bash -lc $probe
    if ($LASTEXITCODE -eq 0) { Say "$process already running; not starting duplicate." }
    else {
        Say "Starting $process..."
        $start = "$setup && exec ros2 run $pkg $exe"
        Invoke-Wsl "docker exec -d $cn bash -lc $(Quote-Sh $start)" | Out-Null
        Start-Sleep -Seconds 2
    }
}

# Open the Ubuntu shell (not the container) and the Docker shell separately.
if (-not $NoShellWindows) {
    Say 'Opening Ubuntu WSL terminal...'
    Start-ShellWindow 'ROVER - Ubuntu WSL' 'exec bash -i'
    Say 'Opening interactive ROS 2 Docker terminal...'
    $shell = "exec docker exec -it -w $(Quote-Sh $Workspace) $cn bash -i"
    Start-ShellWindow 'ROVER - cometbot_dev Docker' $shell
}
if (-not $NoJoyMonitor) {
    Say 'Opening live /joy input window...'
    $watch = "exec docker exec -i $cn bash -lc $(Quote-Sh "$setup && ros2 topic echo /joy")"
    Start-ShellWindow 'ROVER - Live Stadia Inputs (/joy)' $watch
}
Say 'Checking published ROS 2 topics...'
Invoke-Wsl "docker exec $cn bash -lc $(Quote-Sh "$setup && ros2 topic list -t")" | Out-Null
Write-Host ''
Write-Host 'Startup sequence finished. Confirm /joy and /cmd_vel, load ROVERFALLS.usd, then press Play.' -ForegroundColor Green
Write-Host 'WARNING: Seeing /cmd_vel in Docker does NOT prove Isaac Sim receives it.' -ForegroundColor Yellow
Write-Host 'If Isaac Sim Twist outputs remain zero, investigate cross-host Fast DDS discovery / firewall.' -ForegroundColor Yellow
Write-Host 'Reruns do not intentionally duplicate the ROS nodes. Closing terminals does not stop the Docker daemon.'
