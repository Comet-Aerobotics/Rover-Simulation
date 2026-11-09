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
function Invoke-WslBash([string]$command,[switch]$AsRoot){
  # PowerShell 5.1 rewrites quotes inside native process arguments. Pass only
  # base64 ASCII across that boundary and source the original script in Bash.
  $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($command))
  if($AsRoot){& wsl.exe -d $distro --user root --exec bash -lc "source <(printf %s $payload | base64 -d)"}
  else{& wsl.exe -d $distro --exec bash -lc "source <(printf %s $payload | base64 -d)"}
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
function Set-RepoEnvValue([string]$name,[string]$value){
  $envPath=Join-Path $repo '.env'
  if(-not (Test-Path $envPath) -and (Test-Path (Join-Path $repo '.env.example'))){Copy-Item (Join-Path $repo '.env.example') $envPath}
  $lines=[System.Collections.Generic.List[string]]::new()
  if(Test-Path $envPath){Get-Content $envPath | ForEach-Object {$lines.Add($_)}}
  $pattern='^'+[regex]::Escape($name)+'='
  $found=$false
  for($i=0;$i -lt $lines.Count;$i++){
    if($lines[$i] -match $pattern){$lines[$i]="$name=$value";$found=$true;break}
  }
  if(-not $found){$lines.Add("$name=$value")}
  [System.IO.File]::WriteAllLines($envPath,$lines,[System.Text.UTF8Encoding]::new($false))
  [Environment]::SetEnvironmentVariable($name,$value,'Process')
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
  $usbRows=@($usbOutput | Where-Object { $_ -match '^\s*\d+-\d+' })
  $controllerRows=@($usbRows | Where-Object { $_ -match '(?i)controller|gamepad|game pad|joystick' })
  $rowsToAttach=@($controllerRows)
  if($rowsToAttach.Count -eq 0){
    $ambiguousRows=@($usbRows | Where-Object { $_ -match '(?i)USB Input Device|HID-compliant' })
    if($ambiguousRows.Count -gt 0 -and $Mode -eq 'Start'){
      Write-Host 'Windows reports generic input devices. Select the controller device(s), not a keyboard or mouse; use comma-separated numbers for a split controller.'
      for($i=0;$i -lt $ambiguousRows.Count;$i++){Write-Host "  [$($i+1)] $($ambiguousRows[$i].Trim())"}
      $usbChoice=Read-Host 'Local USB device numbers to attach'
      foreach($part in ($usbChoice -split ',')){
        $part=$part.Trim()
        if($part -match '^\d+$' -and [int]$part -ge 1 -and [int]$part -le $ambiguousRows.Count){$rowsToAttach+= $ambiguousRows[[int]$part-1]}
      }
    }
  }
  foreach($usbRow in $rowsToAttach){
    $busid=[regex]::Match($usbRow,'^\s*(\d+-\d+)').Groups[1].Value
    if(-not $busid -or $usbRow -match '(?i)attached'){continue}
    Write-Host "Attaching selected USB input $busid to WSL"
    & usbipd.exe attach --wsl --busid $busid
    if($LASTEXITCODE -ne 0){Write-Warning "Could not attach USB input $busid; continuing with devices already visible in WSL."}
  }
  if($rowsToAttach.Count -eq 0){Write-Host 'No named USB controller found here; checking WSL and the configured remote USB host.'}
} elseif($usbipdCommand){Write-Warning 'usbipd list failed; check USB attachment manually.'}
$remoteUsbHost=$env:ROVER_REMOTE_USB_HOST
$configuredRemoteUsbHost=$remoteUsbHost
$tailscaleCommand=Get-Command 'tailscale.exe' -ErrorAction SilentlyContinue
if($Mode -eq 'Start' -and $tailscaleCommand){
  Invoke-WslBash 'command -v usbip >/dev/null 2>&1'
  if($LASTEXITCODE -eq 0){
    try{
      $tailnetStatus=(& $tailscaleCommand.Path status --json | ConvertFrom-Json)
      $remoteCandidates=@()
      foreach($peerProperty in $tailnetStatus.Peer.PSObject.Properties){
        $peer=$peerProperty.Value
        if(-not $peer.Online -or $peer.HostName -eq $tailnetStatus.Self.HostName){continue}
        $peerIp=@($peer.TailscaleIPs | Where-Object {$_ -match '^\d{1,3}(\.\d{1,3}){3}$'} | Select-Object -First 1)
        if($peerIp.Count -eq 0){continue}
        $portOpen=Test-NetConnection -ComputerName $peerIp[0] -Port 3240 -InformationLevel Quiet -WarningAction SilentlyContinue
        if(-not $portOpen){continue}
        $peerUsbList=@(Invoke-WslBash "usbip list --remote='$($peerIp[0])'")
        if($LASTEXITCODE -ne 0){continue}
        $peerDevices=@($peerUsbList | Where-Object {$_ -match '^\s*\d+-\d+:'})
        if($peerDevices.Count -gt 0){$remoteCandidates+= [pscustomobject]@{Host=$peerIp[0];Name=$peer.HostName;Devices=$peerDevices}}
      }
      $preferredCandidate=@($remoteCandidates | Where-Object {$_.Host -eq $remoteUsbHost -or $_.Name -eq $remoteUsbHost})
      if($remoteCandidates.Count -gt 1){
        Write-Host 'USB controllers are shared by multiple online Tailscale computers:'
        for($i=0;$i -lt $remoteCandidates.Count;$i++){Write-Host "  [$($i+1)] $($remoteCandidates[$i].Name) ($($remoteCandidates[$i].Host)): $($remoteCandidates[$i].Devices.Count) USB device(s)"}
        $defaultPeer=if($preferredCandidate.Count -gt 0){[array]::IndexOf(@($remoteCandidates.Host),$preferredCandidate[0].Host)+1}else{1}
        $peerChoice=Read-Host "Choose the controller computer (Enter for saved choice or 1) [$defaultPeer]"
        if([string]::IsNullOrWhiteSpace($peerChoice)){$peerChoice=[string]$defaultPeer}
        if($peerChoice -match '^\d+$' -and [int]$peerChoice -ge 1 -and [int]$peerChoice -le $remoteCandidates.Count){$remoteUsbHost=$remoteCandidates[[int]$peerChoice-1].Host}
        else{throw 'Enter one of the listed computer numbers.'}
      } elseif($remoteCandidates.Count -eq 1){$remoteUsbHost=$remoteCandidates[0].Host}
      elseif([string]::IsNullOrWhiteSpace($remoteUsbHost)){
        Write-Host 'No online Tailscale computer is currently sharing USB/IP devices.'
      }
      if(-not [string]::IsNullOrWhiteSpace($remoteUsbHost)){
        if(-not [string]::IsNullOrWhiteSpace($configuredRemoteUsbHost) -and $remoteUsbHost -ne $configuredRemoteUsbHost){
          Set-RepoEnvValue 'ROVER_REMOTE_USB_BUSIDS' ''
        }
        Set-RepoEnvValue 'ROVER_REMOTE_USB_HOST' $remoteUsbHost
        Write-Host "Using Tailscale USB host $remoteUsbHost. Saved it in this computer's ignored .env file."
      }
    } catch {Write-Warning "Automatic Tailscale USB/IP discovery failed: $($_.Exception.Message)"}
  }
}
if(-not [string]::IsNullOrWhiteSpace($remoteUsbHost)){
  if($remoteUsbHost -notmatch '^[A-Za-z0-9.-]+$'){throw 'ROVER_REMOTE_USB_HOST must be a Tailscale hostname or IPv4 address.'}
  Write-Host "Checking USB controllers shared by remote computer '$remoteUsbHost'."
  Invoke-WslBash 'command -v usbip >/dev/null 2>&1'
  if($LASTEXITCODE -ne 0){throw "The USB/IP client is not installed in WSL. Run: sudo apt update && sudo apt install linux-tools-virtual hwdata; then follow the usbipd-win WSL-support instructions to put the usbip client on PATH."}
  $remoteList=@(Invoke-WslBash "usbip list --remote='$remoteUsbHost'" -AsRoot)
  $remoteListExit=$LASTEXITCODE
  if($remoteListExit -ne 0){Write-Warning "Could not list USB devices from '$remoteUsbHost'. Check Tailscale connectivity, the remote usbipd service, and TCP port 3240."}
  else{
    $remoteList | ForEach-Object {Write-Host $_}
    $remoteDeviceRows=@($remoteList | Where-Object { $_ -match '^\s*\d+-\d+:' })
    $namedControllerRows=@($remoteDeviceRows | Where-Object { $_ -match '(?i)controller|gamepad|game pad|joystick' })
    $remoteRowsToAttach=@()
    $configuredRemoteBusIds=@($env:ROVER_REMOTE_USB_BUSIDS -split ',' | ForEach-Object {$_.Trim()} | Where-Object {$_})
    if($configuredRemoteBusIds.Count -gt 0){
      $remoteRowsToAttach=@($remoteDeviceRows | Where-Object {
        $rowBusId=[regex]::Match($_,'^\s*(\d+-\d+):').Groups[1].Value
        $configuredRemoteBusIds -contains $rowBusId
      })
      $exportedBusIds=@($remoteDeviceRows | ForEach-Object {[regex]::Match($_,'^\s*(\d+-\d+):').Groups[1].Value})
      $missingBusIds=@($configuredRemoteBusIds | Where-Object {$_ -notin $exportedBusIds})
      if($missingBusIds.Count -gt 0 -or $remoteRowsToAttach.Count -ne $configuredRemoteBusIds.Count){
        Write-Warning "Saved remote USB device IDs are not available ($($missingBusIds -join ', ')); rediscovering from this computer."
        $remoteRowsToAttach=@()
        $configuredRemoteBusIds=@()
        Set-RepoEnvValue 'ROVER_REMOTE_USB_BUSIDS' ''
      }
    }
    if($configuredRemoteBusIds.Count -eq 0 -and ($remoteDeviceRows.Count -eq 1 -or ($namedControllerRows.Count -gt 0 -and $namedControllerRows.Count -eq $remoteDeviceRows.Count))){
      $remoteRowsToAttach=if($namedControllerRows.Count -gt 0){$namedControllerRows}else{$remoteDeviceRows}
    } elseif($configuredRemoteBusIds.Count -eq 0 -and $remoteDeviceRows.Count -gt 0 -and $Mode -eq 'Start'){
      Write-Host 'The remote USB server has shared devices with generic names. Select the controller device(s) to attach; you can enter multiple numbers separated by commas.'
      for($i=0;$i -lt $remoteDeviceRows.Count;$i++){Write-Host "  [$($i+1)] $($remoteDeviceRows[$i].Trim())"}
      $remoteChoice=Read-Host 'Remote device numbers to attach (comma-separated)'
      foreach($part in ($remoteChoice -split ',')){
        $part=$part.Trim()
        if($part -match '^\d+$' -and [int]$part -ge 1 -and [int]$part -le $remoteDeviceRows.Count){
          $remoteRowsToAttach+= $remoteDeviceRows[[int]$part-1]
        }
      }
      if($remoteRowsToAttach.Count -eq 0){throw 'No valid remote USB devices were selected.'}
      $selectedRemoteBusIds=@($remoteRowsToAttach | ForEach-Object {[regex]::Match($_,'^\s*(\d+-\d+):').Groups[1].Value})
      Set-RepoEnvValue 'ROVER_REMOTE_USB_BUSIDS' ($selectedRemoteBusIds -join ',')
      Write-Host "Saved the selected remote USB device IDs in this computer's ignored .env file."
    }
    foreach($remoteRow in $remoteRowsToAttach){
      $remoteBusId=[regex]::Match($remoteRow,'^\s*(\d+-\d+):').Groups[1].Value
      if(-not $remoteBusId){continue}
      Write-Host "Attaching remote USB controller device $remoteBusId into WSL."
      Invoke-WslBash "usbip attach --remote='$remoteUsbHost' --busid='$remoteBusId'" -AsRoot
      if($LASTEXITCODE -ne 0){Write-Warning "USB/IP attach for $remoteBusId returned an error; it may already be attached. Continuing to check WSL input devices."}
    }
    if($remoteDeviceRows.Count -eq 0){Write-Warning 'No USB devices are shared by the remote computer. Bind the controller device(s) there with usbipd, then retry.'}
  }
} else {
  if($Mode -eq 'Diagnostics'){Write-Host 'No preferred remote USB host is saved; Start mode will discover USB/IP devices on online Tailscale peers.'}
  else{Write-Host 'No remote USB/IP controller was discovered; only local or already-attached WSL controllers can be used.' -ForegroundColor Yellow}
}
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
$selectedJoysticks=@()
$joyLayout='single'
if($joysticks.Count -gt 1){
  Write-Host 'Joystick devices available in WSL:'
  for($i=0;$i -lt $joysticks.Count;$i++){Write-Host "  [$($i+1)] $($joysticks[$i].Name) ($($joysticks[$i].Path))"}
  $choice=Read-Host 'Choose one device (1) or a split-controller pair (1,2)'
  if($choice -match '^\s*(\d+)\s*,\s*(\d+)\s*$'){
    $first=[int]$matches[1];$second=[int]$matches[2]
    if($first -lt 1 -or $first -gt $joysticks.Count -or $second -lt 1 -or $second -gt $joysticks.Count -or $first -eq $second){throw 'Enter two different valid controller numbers for a pair.'}
    $selectedJoysticks=@($joysticks[$first-1],$joysticks[$second-1])
    $joyLayout='pair'
  } elseif($choice -match '^\s*\d+\s*$' -and [int]$choice -ge 1 -and [int]$choice -le $joysticks.Count){
    $selectedJoysticks=@($joysticks[[int]$choice-1])
  } else{throw 'Enter one controller number or two different numbers separated by a comma.'}
} else{$selectedJoysticks=@($joysticks[0])}
$selectedDevices=@($selectedJoysticks | ForEach-Object {$_.Path})
$selectedDeviceIds=@($selectedJoysticks | ForEach-Object {$_.Id}) -join ','
Write-Host "Selected controller device(s): $($selectedJoysticks.Name -join ', ') ($($selectedDevices -join ', ')); layout=$joyLayout."
foreach($selectedDevice in $selectedDevices){
  if(-not ($selectedDevice -match '^/dev/input/js\d+$')){throw "Unexpected joystick device path '$selectedDevice'."}
}
if($container -eq 'aiaa_rover_dev' -and ($legacyNodes -match '/joy_node' -or $legacyNodes -match '/teleop_publisher')){
  throw 'Legacy teleop is active in cometbot_dev. Run scripts/windows/stop_rover.ps1 -Container cometbot_dev, verify its Joy/teleop nodes exit, then retry.'
}
$pythonPaths=($selectedDevices | ForEach-Object {'"' + $_ + '"'}) -join ','
$inputProbe="docker exec $container python3 -c 'import os; paths=[$pythonPaths]; fds=[os.open(p,os.O_RDONLY|os.O_NONBLOCK) for p in paths]; [os.close(fd) for fd in fds]'"
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
  $firstDeviceId=$selectedJoysticks[0].Id
  $secondDeviceId=if($selectedJoysticks.Count -gt 1){$selectedJoysticks[1].Id}else{$firstDeviceId}
  Invoke-WslBash "cd '$linuxRepo' && ROVER_JOY_DEVICE_ID=$firstDeviceId ROVER_JOY_DEVICE_ID_2=$secondDeviceId docker compose -f docker/compose.yaml up -d --build$recreate"
  if($LASTEXITCODE -ne 0){throw 'Compose build/start failed on the WSL Docker engine.'}
}
Invoke-WslBash $inputProbe 2>$null
$containerHasJoystick=$LASTEXITCODE -eq 0
if(-not $containerHasJoystick){throw "WSL sees the selected controller device(s), but container '$container' cannot open them. Stop teleop and recreate the container to apply its device access rules."}
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
  Invoke-WslBash "docker exec -d -e ROVER_JOY_LAYOUT=$joyLayout -e ROVER_JOY_DEVICE_IDS='$selectedDeviceIds' $container bash -lc '$teleopCommand'"
  if($LASTEXITCODE -ne 0){throw 'Could not start the ROS teleoperation launch in the rover container.'}
}
$monitorTopics=if($joyLayout -eq 'pair'){'ros2 topic echo /joy_left & ros2 topic echo /joy_right & wait'}else{'ros2 topic echo /joy'}
$monitor="docker exec -it $container bash -lc 'source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && $monitorTopics'"
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
