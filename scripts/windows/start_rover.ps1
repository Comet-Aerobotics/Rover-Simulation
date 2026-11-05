[CmdletBinding()]
param([ValidateSet('Diagnostics','Start')][string]$Mode='Diagnostics')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if(Test-Path (Join-Path $repo '.env')) {
  Get-Content (Join-Path $repo '.env') | ForEach-Object {
    if($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1],$matches[2].Trim(),'Process') }
  }
}
$distro=if($env:WSL_DISTRO){$env:WSL_DISTRO}else{'Ubuntu'}
$container=if($env:ROS_CONTAINER){$env:ROS_CONTAINER}else{'aiaa_rover_dev'}
function Start-WslWindow([string]$title,[string]$command){
  $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($command))
  $child=@'
$Host.UI.RawUI.WindowTitle='TITLE_VALUE'
$scriptText=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('PAYLOAD_VALUE'))
& wsl.exe -d 'DISTRO_VALUE' -- bash -lc $scriptText
if($LASTEXITCODE -ne 0){Write-Host "WSL command exited with code $LASTEXITCODE" -ForegroundColor Yellow}
'@
  $child=$child.Replace('TITLE_VALUE',$title).Replace('PAYLOAD_VALUE',$payload).Replace('DISTRO_VALUE',$distro)
  $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
  Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoLogo','-NoProfile','-NoExit','-EncodedCommand',$encoded) -WindowStyle Normal | Out-Null
}
Write-Host "Repository: $repo`nWSL distro: $distro`nROS container: $container`nMode: $Mode"
& wsl.exe -d $distro --exec true 2>$null
if($LASTEXITCODE -ne 0){throw "WSL distro '$distro' could not start."}
$ctx=& wsl.exe -d $distro --exec bash -lc 'docker context show'
if($LASTEXITCODE -ne 0){throw "Docker CLI inside WSL distro '$distro' cannot reach its engine."}
Write-Host "WSL Docker context: $ctx"
$usbOutput=@(& usbipd.exe list)
$usbExit=$LASTEXITCODE
$usbOutput | ForEach-Object {Write-Host $_}
if($usbExit -eq 0){
  $controllerRows=@($usbOutput | Where-Object { $_ -match '(?i)stadia|google.*controller' -and $_ -match '^\s*\d+-\d+' })
  if($controllerRows.Count -eq 1){
    $busid=[regex]::Match($controllerRows[0],'^\s*(\d+-\d+)').Groups[1].Value
    if($controllerRows[0] -notmatch '(?i)attached'){Write-Host "Attaching identified controller $busid to WSL"; & usbipd.exe attach --wsl --busid $busid}
    else{Write-Host "Controller $busid is already attached."}
  } elseif($controllerRows.Count -gt 1){Write-Warning 'Multiple Stadia/Google controller matches; no device attached automatically.'}
  else{Write-Warning 'No Stadia controller identified. Attach it manually if needed.'}
} else{Write-Warning 'usbipd unavailable; check USB attachment manually.'}
Write-Host 'WSL input devices:'
& wsl.exe -d $distro --exec sh -lc 'ls -l /dev/input/js* /dev/input/event* 2>/dev/null || true'
$dockerPs=& wsl.exe -d $distro --exec bash -lc 'docker ps --format "{{.Names}} {{.Status}}"'
if($LASTEXITCODE -ne 0){throw 'Could not list containers on the WSL Docker engine.'}
Write-Host "WSL containers:`n$($dockerPs -join "`n")"
$oldState=& wsl.exe -d $distro --exec bash -lc 'docker inspect -f "{{.State.Status}}" cometbot_dev 2>/dev/null'
$oldExit=$LASTEXITCODE
$targetState=& wsl.exe -d $distro --exec bash -lc "docker inspect -f '{{.State.Status}}' $container 2>/dev/null"
$targetExit=$LASTEXITCODE
if($targetExit -eq 0){
  Write-Host "Target container state: $targetState"
  & wsl.exe -d $distro --exec bash -lc "docker exec $container bash -lc 'source /opt/ros/humble/setup.bash; if [ -f /workspace/install/setup.bash ]; then source /workspace/install/setup.bash; elif [ -f /root/CAN/cometbot_ws/install/setup.bash ]; then source /root/CAN/cometbot_ws/install/setup.bash; fi; printenv ROS_DISTRO ROS_DOMAIN_ID RMW_IMPLEMENTATION; ros2 node list 2>/dev/null; ros2 topic info /joy 2>/dev/null; ros2 topic info /cmd_vel 2>/dev/null'"
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
if($container -eq 'aiaa_rover_dev' -and ($legacyNodes -match '/joy_node' -or $legacyNodes -match '/teleop_publisher')){
  throw 'Legacy teleop is active in cometbot_dev. Run scripts/windows/stop_rover.ps1 -Container cometbot_dev, verify its Joy/teleop nodes exit, then retry.'
}
if($targetState -ne 'running'){
  $linuxRepo=(& wsl.exe -d $distro --exec wslpath -a $repo).Trim()
  if($LASTEXITCODE -ne 0){throw 'Could not map the repository path into WSL.'}
  & wsl.exe -d $distro --exec bash -lc "cd '$linuxRepo' && docker compose -f docker/compose.yaml up -d --build"
  if($LASTEXITCODE -ne 0){throw 'Compose build/start failed on the WSL Docker engine.'}
}
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
  & wsl.exe -d $distro --exec docker exec -d $container bash -lc $teleopCommand
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
for($attempt=0;$attempt -lt 20;$attempt++){
  $nodeProcesses=@(& wsl.exe -d $distro --exec docker exec $container ps -eo args=)
  if($LASTEXITCODE -ne 0){throw "Could not inspect processes in '$container'."}
  $hasJoy=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])joy_node([ /]|$)' }).Count -gt 0
  $hasTeleop=@($nodeProcesses | Where-Object { $_ -match '(^|[ /])teleop_publisher([ /]|$)' }).Count -gt 0
  if($hasJoy -and $hasTeleop){$healthy=$true;break}
  Start-Sleep -Seconds 1
}
if(-not $healthy){throw 'ROS launch did not expose both expected nodes within 20 seconds; inspect the opened terminals.'}
& wsl.exe -d $distro --exec docker exec $container bash -lc 'source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && ros2 topic info /joy && ros2 topic info /cmd_vel'
$isaacLauncher=Join-Path $PSScriptRoot 'start_isaac_sim.ps1'
$scene=if($env:ROVER_SCENE){$env:ROVER_SCENE}else{'scenes/CAMERASYNCSSMOETIMES.usd'}
& $isaacLauncher -Scene $scene
Write-Host 'Startup commands issued. Confirm ROS Bridge and end-to-end command delivery in Isaac Sim.'
