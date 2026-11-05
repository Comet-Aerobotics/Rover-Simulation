[CmdletBinding()]
param([string]$Container,[string]$Distro)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$envFile=Join-Path $repo '.env'
if (Test-Path -LiteralPath $envFile) { Get-Content $envFile | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {[Environment]::SetEnvironmentVariable($matches[1],$matches[2].Trim(),'Process')} } }
if(-not $Distro){$Distro=if($env:WSL_DISTRO){$env:WSL_DISTRO}else{'Ubuntu'}}
if (-not $Container) { $Container=if ($env:ROS_CONTAINER) {$env:ROS_CONTAINER} else {'aiaa_rover_dev'} }
$state=& wsl.exe -d $Distro --exec bash -lc "docker inspect -f '{{.State.Running}}' $Container 2>/dev/null"
if($LASTEXITCODE -ne 0){Write-Host "Container $Container is not present in WSL Docker; no changes made.";return}
if ($state -eq 'true') {
  & wsl.exe -d $Distro --exec bash -lc "docker exec $Container pkill -INT -f '[r]os2 launch cometbot_control.teleop.launch.py' 2>/dev/null || true"
  & wsl.exe -d $Distro --exec bash -lc "docker exec $Container pkill -INT -f '[t]eleop_publisher' 2>/dev/null || true"
  & wsl.exe -d $Distro --exec bash -lc "docker exec $Container pkill -INT -f '[j]oy_node' 2>/dev/null || true"
  Write-Host "Sent SIGINT to the managed teleop launch and its two known nodes in $Container. The container remains running."
} else { Write-Host "Container $Container is stopped; no container changes made." }
Write-Host 'Isaac Sim is left open to protect unsaved stage edits. Stop or save it interactively.'
