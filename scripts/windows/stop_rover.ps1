[CmdletBinding()]
param([string]$Container,[string]$Distro,[switch]$WhatIf)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$envFile=Join-Path $repo '.env'
if (Test-Path -LiteralPath $envFile) { Get-Content $envFile | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {[Environment]::SetEnvironmentVariable($matches[1],$matches[2].Trim(),'Process')} } }
if(-not $Distro){$Distro=if($env:WSL_DISTRO){$env:WSL_DISTRO}else{'Ubuntu'}}
if (-not $Container) { $Container=if ($env:ROS_CONTAINER) {$env:ROS_CONTAINER} else {'aiaa_rover_dev'} }
$state=& wsl.exe -d $Distro --exec bash -lc "docker inspect -f '{{.State.Running}}' $Container 2>/dev/null"
if($LASTEXITCODE -ne 0){Write-Host "Container $Container is not present in WSL Docker; no changes made.";return}
if ($state -eq 'true') {
  # docker exec ps/pkill sees every host process when a legacy container uses
  # pid: host. docker top scopes the list to the selected container's cgroup.
  $processRows = @(& wsl.exe -d $Distro --exec docker top $Container -eo pid,args)
  if ($LASTEXITCODE -ne 0) { throw "Could not list processes owned by $Container; no signals sent." }
  $controlPids = @(
    foreach ($row in $processRows) {
      if ($row -match '^\s*(\d+)\s+(.+)$') {
        $pidNumber = [int]$matches[1]
        $command = $matches[2]
      } else { continue }
      if ($command -match '(?:^|/)ros2 launch cometbot_control teleop\.launch\.py' -or
          $command -match '(?:^|/)teleop_publisher(?:\s|$)' -or
          $command -match '(?:^|/)joy_node(?:\s|$)') {
        $pidNumber
      }
    }
  ) | Sort-Object -Unique
  foreach ($pidNumber in $controlPids) {
    if ($WhatIf) { Write-Host "Would send SIGINT to PID $pidNumber in $Container."; continue }
    & wsl.exe -d $Distro --user root --exec kill -INT $pidNumber
    if ($LASTEXITCODE -ne 0) { Write-Warning "Could not signal PID $pidNumber in $Container." }
  }
  if (-not $WhatIf) { Write-Host "Sent SIGINT to $($controlPids.Count) container-owned teleop process(es) in $Container. The container remains running." }
} else { Write-Host "Container $Container is stopped; no container changes made." }
Write-Host 'Isaac Sim is left open to protect unsaved stage edits. Stop or save it interactively.'
