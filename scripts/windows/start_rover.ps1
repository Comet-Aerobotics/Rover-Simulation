[CmdletBinding()]
param([ValidateSet('Diagnostics','Start')][string]$Mode='Diagnostics',[switch]$SandDeformation)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if(Test-Path (Join-Path $repo '.env')) {
  Get-Content (Join-Path $repo '.env') | ForEach-Object {
    if($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1],$matches[2].Trim(),'Process') }
  }
}
$distro=if($env:WSL_DISTRO){$env:WSL_DISTRO}else{'Ubuntu'}
$container=if($env:ROS_CONTAINER){$env:ROS_CONTAINER}else{'aiaa_rover_dev'}
function Invoke-WslBash([string]$command){
  # PowerShell 5.1 rewrites quotes inside native process arguments. Pass only
  # base64 ASCII across that boundary and source the original script in Bash.
  $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($command))
  & wsl.exe -d $distro --exec bash -lc "source <(printf %s $payload | base64 -d)"
}
function Start-WslWindow([string]$title,[string]$command){
  $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($command))
  $child=@'
$Host.UI.RawUI.WindowTitle='TITLE_VALUE'
& wsl.exe -d 'DISTRO_VALUE' --exec bash -lc 'source <(printf %s PAYLOAD_VALUE | base64 -d)'
if($LASTEXITCODE -ne 0){Write-Host "WSL command exited with code $LASTEXITCODE" -ForegroundColor Yellow}
'@
  $child=$child.Replace('TITLE_VALUE',$title).Replace('PAYLOAD_VALUE',$payload).Replace('DISTRO_VALUE',$distro)
  $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
  Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoLogo','-NoProfile','-NoExit','-EncodedCommand',$encoded) -WindowStyle Normal | Out-Null
}
Write-Host "Repository: $repo`nWSL distro: $distro`nROS container: $container`nMode: $Mode"
& wsl.exe -d $distro --exec true 2>$null
if($LASTEXITCODE -ne 0){throw "WSL distro '$distro' could not start."}
$ctx=Invoke-WslBash 'docker context show'
if($LASTEXITCODE -ne 0){throw "Docker CLI inside WSL distro '$distro' cannot reach its engine."}
Write-Host "WSL Docker context: $ctx"
$usbipdCommand=Get-Command 'usbipd.exe' -ErrorAction SilentlyContinue
$usbOutput=@()
$usbExit=1
if($usbipdCommand){
  $usbOutput=@(& $usbipdCommand.Path list)
  $usbExit=$LASTEXITCODE
  $usbOutput | ForEach-Object {Write-Host $_}
} else{Write-Host 'usbipd-win is not installed on this computer; checking WSL-visible controllers only.'}
if($usbExit -eq 0){
  $controllerRows=@($usbOutput | Where-Object { $_ -match '(?i)controller|gamepad|game pad|joystick|joy-con|dualshock|dualsense|stadia|xbox' -and $_ -match '^\s*\d+-\d+' })
  if($controllerRows.Count -gt 0){
    $selectedUsbRow=$controllerRows[0]
    if($controllerRows.Count -gt 1 -and $Mode -eq 'Start'){
      Write-Host 'USB controllers available on this Windows computer:'
      for($i=0;$i -lt $controllerRows.Count;$i++){Write-Host "  [$($i+1)] $($controllerRows[$i].Trim())"}
      $usbChoice=Read-Host 'Choose a controller to attach to WSL (Enter for 1)'
      if([string]::IsNullOrWhiteSpace($usbChoice)){$usbChoice='1'}
      if($usbChoice -notmatch '^\d+$' -or [int]$usbChoice -lt 1 -or [int]$usbChoice -gt $controllerRows.Count){throw 'Invalid controller selection.'}
      $selectedUsbRow=$controllerRows[[int]$usbChoice-1]
    }
    $busid=[regex]::Match($selectedUsbRow,'^\s*(\d+-\d+)').Groups[1].Value
    if($selectedUsbRow -notmatch '(?i)attached'){
      Write-Host "Attaching selected controller $busid to WSL"
      & usbipd.exe attach --wsl --busid $busid
      if($LASTEXITCODE -ne 0){throw "Could not attach controller $busid to WSL."}
    }
    else{Write-Host "Controller $busid is already attached to WSL."}
  } else{Write-Host 'No controller on this Windows computer; checking WSL for local or USB-over-IP controllers.'}
} elseif($usbipdCommand){Write-Warning 'usbipd list failed; check USB attachment manually.'}
$listJoysticks='for j in /dev/input/js[0-9]*; do [ -e "$j" ] || continue; n=${j##*js}; name=$(cat "/sys/class/input/js${n}/device/name" 2>/dev/null || printf "Unknown controller"); printf "%s\t%s\n" "$j" "$name"; done'
$wslJoystickRows=@(Invoke-WslBash $listJoysticks)
if($LASTEXITCODE -ne 0){throw 'Could not enumerate joystick devices in WSL.'}
Write-Host 'Controllers visible to WSL (including USB-over-IP devices):'
if($wslJoystickRows.Count -eq 0){Write-Host '  None detected.'}else{$wslJoystickRows | ForEach-Object {Write-Host "  $_"}}
$dockerPs=Invoke-WslBash 'docker ps --format "{{.Names}} {{.Status}}"'
if($LASTEXITCODE -ne 0){throw 'Could not list containers on the WSL Docker engine.'}
Write-Host "WSL containers:`n$($dockerPs -join "`n")"
$oldState=Invoke-WslBash 'docker inspect -f "{{.State.Status}}" cometbot_dev 2>/dev/null'
$oldExit=$LASTEXITCODE
$targetState=Invoke-WslBash "docker inspect -f '{{.State.Status}}' $container 2>/dev/null"
$targetExit=$LASTEXITCODE
if($targetExit -eq 0){
  Write-Host "Target container state: $targetState"
  if($targetState -eq 'running'){
    Invoke-WslBash "docker exec $container bash -lc 'source /opt/ros/humble/setup.bash; if [ -f /workspace/install/setup.bash ]; then source /workspace/install/setup.bash; elif [ -f /root/CAN/cometbot_ws/install/setup.bash ]; then source /root/CAN/cometbot_ws/install/setup.bash; fi; printenv ROS_DISTRO ROS_DOMAIN_ID RMW_IMPLEMENTATION; ros2 node list 2>/dev/null; ros2 topic info /joy 2>/dev/null; ros2 topic info /cmd_vel 2>/dev/null'"
  }
} else{Write-Host "Target container '$container' is not present on WSL Docker."}
$legacyNodes=@()
if($oldExit -eq 0 -and $oldState -eq 'running'){
  $legacyProcesses=@(& wsl.exe -d $distro --exec docker exec cometbot_dev ps -eo args=)
  if($LASTEXITCODE -ne 0){throw 'Could not verify legacy ROS nodes; refusing to launch duplicate services.'}
  $legacyControlProcesses=@($legacyProcesses | Where-Object { $_ -match '/root/CAN/cometbot_ws' -and $_ -match '(^|[ /])joy_node([ /]|$)|(^|[ /])teleop_publisher([ /]|$)|ros2 launch cometbot_control\.teleop\.launch\.py' })
  if(@($legacyControlProcesses | Where-Object { $_ -match 'joy_node' }).Count -gt 0){$legacyNodes+='/joy_node'}
  if(@($legacyControlProcesses | Where-Object { $_ -match 'teleop_publisher' }).Count -gt 0){$legacyNodes+='/teleop_publisher'}
  Write-Host "Legacy cometbot_dev nodes: $($legacyNodes -join ', ')"
}
if($Mode -eq 'Diagnostics'){return}
for($attempt=0;$attempt -lt 10 -and $wslJoystickRows.Count -eq 0;$attempt++){
  Start-Sleep -Seconds 1
  $wslJoystickRows=@(Invoke-WslBash $listJoysticks)
}
if($wslJoystickRows.Count -eq 0){throw 'No controller is visible in WSL. Attach the local controller with usbipd or connect the remote USB-over-IP device into WSL, then retry.'}
$joysticks=@($wslJoystickRows | ForEach-Object {
  if($_ -match '^(?<path>/dev/input/js(?<id>\d+))\s+(?<name>.*)$'){
    [pscustomobject]@{Path=$matches.path;Id=[int]$matches.id;Name=$matches.name.Trim()}
  }
} | Where-Object {$_})
if($joysticks.Count -eq 0){throw 'WSL reported input devices, but no usable joystick device names could be parsed.'}
$selectedJoystick=$joysticks[0]
if($joysticks.Count -gt 1){
  Write-Host 'Multiple controllers are available:'
  for($i=0;$i -lt $joysticks.Count;$i++){Write-Host "  [$($i+1)] $($joysticks[$i].Name) ($($joysticks[$i].Path))"}
  $choice=Read-Host 'Choose the controller for rover teleoperation'
  if($choice -notmatch '^\d+$' -or [int]$choice -lt 1 -or [int]$choice -gt $joysticks.Count){throw 'Invalid controller selection.'}
  $selectedJoystick=$joysticks[[int]$choice-1]
} else{Write-Host "Using $($selectedJoystick.Name) ($($selectedJoystick.Path))."}
$selectedDevice=$selectedJoystick.Path
$selectedDeviceId=$selectedJoystick.Id
Write-Host "Selected controller: $($selectedJoystick.Name) at $selectedDevice (joy device ID $selectedDeviceId)."
if(-not ($selectedDevice -match '^/dev/input/js\d+$')){
  throw "Unexpected joystick device path '$selectedDevice'."
}
if($container -eq 'aiaa_rover_dev' -and ($legacyNodes -match '/joy_node' -or $legacyNodes -match '/teleop_publisher')){
  throw 'Legacy teleop is active in cometbot_dev. Run scripts/windows/stop_rover.ps1 -Container cometbot_dev, verify its Joy/teleop nodes exit, then retry.'
}
$inputProbe='docker exec CONTAINER python3 -c "import os; p=''jsN''; fd=os.open(p,os.O_RDONLY|os.O_NONBLOCK); os.close(fd)"'
$inputProbe=$inputProbe.Replace('CONTAINER',$container).Replace('jsN',$selectedDevice)
$containerHasJoystick=$false
if($targetState -eq 'running'){
  $nodeProcesses=@(& wsl.exe -d $distro --exec docker exec $container ps -eo args=)
  if($LASTEXITCODE -ne 0){throw "Could not inspect processes in '$container'."}
  $hasJoy=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])joy_node([ /]|$)' }).Count -gt 0
  $hasTeleop=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])teleop_publisher([ /]|$)' }).Count -gt 0
  Invoke-WslBash $inputProbe 2>$null
  $containerHasJoystick=$LASTEXITCODE -eq 0
  if(-not $containerHasJoystick -and ($hasJoy -or $hasTeleop)){
    throw "The running '$container' has active teleop nodes but cannot open the input devices. Stop this project's teleop nodes, then rerun Start to recreate the container with the attached controller."
  }
}
if($targetState -ne 'running' -or -not $containerHasJoystick){
  $linuxRepo=(& wsl.exe -d $distro --exec wslpath -a $repo).Trim()
  if($LASTEXITCODE -ne 0){throw 'Could not map the repository path into WSL.'}
  $recreate=if($targetState -eq 'running'){' --force-recreate'}else{''}
  Invoke-WslBash "cd '$linuxRepo' && ROVER_JOYSTICK_DEVICE='$selectedDevice' docker compose -f docker/compose.yaml up -d --build$recreate"
  if($LASTEXITCODE -ne 0){throw 'Compose build/start failed on the WSL Docker engine.'}
}
Invoke-WslBash $inputProbe 2>$null
$containerHasJoystick=$LASTEXITCODE -eq 0
if(-not $containerHasJoystick){throw "WSL sees the controller at $selectedDevice, but container '$container' cannot open it. Check the Docker device mapping."}
$nodeProcesses=@(& wsl.exe -d $distro --exec docker exec $container ps -eo args=)
if($LASTEXITCODE -ne 0){throw "Could not inspect processes in '$container'."}
$hasJoy=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])joy_node([ /]|$)' }).Count -gt 0
$hasTeleop=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])teleop_publisher([ /]|$)' }).Count -gt 0
if($hasJoy -and $hasTeleop){
  Write-Host 'ROS teleoperation nodes are already running; reusing them.'
} elseif($hasJoy -or $hasTeleop){
  throw "Partial ROS teleoperation is already running in '$container'; resolve it before starting another launch."
} else {
  $teleopCommand='source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && ros2 launch cometbot_control teleop.launch.py > /tmp/aiaa_rover_teleop.log 2>&1'
  Invoke-WslBash "docker exec -d -e ROVER_JOY_DEVICE_ID=$selectedDeviceId $container bash -lc '$teleopCommand'"
  if($LASTEXITCODE -ne 0){throw 'Could not start the ROS teleoperation launch in the rover container.'}
}
$monitor="docker exec -it $container bash -lc 'source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && ros2 topic echo /joy'"
Write-Host 'Opening Ubuntu WSL terminal.'
Start-WslWindow 'ROVER - Ubuntu shell' 'exec bash -i'
Write-Host 'Opening Docker shell.'
Start-WslWindow 'ROVER - ROS container shell' "exec docker exec -it -w /workspace $container bash -i"
Write-Host 'Opening /joy controller input monitor.'
Start-WslWindow 'ROVER - /joy monitor' $monitor
$healthy=$false
for($attempt=0;$attempt -lt 60;$attempt++){
  $nodeProcesses=@(& wsl.exe -d $distro --exec docker exec $container ps -eo args=)
  if($LASTEXITCODE -ne 0){throw "Could not inspect processes in '$container'."}
  $hasJoy=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])joy_node([ /]|$)' }).Count -gt 0
  $hasTeleop=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])teleop_publisher([ /]|$)' }).Count -gt 0
  if($hasJoy -and $hasTeleop){$healthy=$true;break}
  Start-Sleep -Seconds 1
}
if(-not $healthy){throw 'ROS launch did not expose both expected nodes within 60 seconds; inspect /tmp/aiaa_rover_teleop.log in the rover container.'}
& wsl.exe -d $distro --exec docker exec $container bash -lc 'source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && ros2 topic info /joy && ros2 topic info /cmd_vel'
$isaacLauncher=Join-Path $PSScriptRoot 'start_isaac_sim.ps1'
$scene=if($env:ROVER_SCENE){$env:ROVER_SCENE}else{'scenes/CAMERASYNCSSMOETIMES.usd'}
if ($SandDeformation -or $env:ROVER_SAND_DEFORMATION -eq '1') {
  & $isaacLauncher -RosDistro 'humble' -SandDeformation
} else {
  & $isaacLauncher -Scene $scene -RosDistro 'humble'
}
Write-Host 'Startup commands issued. Confirm ROS Bridge and end-to-end command delivery in Isaac Sim.'
Write-Host 'Open the configured scene and press Play; the rover Action Graph is driven by simulation playback.'
