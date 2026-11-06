[CmdletBinding()]
param(
    [string]$IsaacRoot,
    [string]$Scene,
    [switch]$SandDeformation,
    [ValidateSet('jazzy', 'humble')]
    [string]$RosDistro = 'humble'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

$envFile = Join-Path $repo '.env'
if (Test-Path -LiteralPath $envFile) {
    Get-Content -LiteralPath $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim(), 'Process')
        }
    }
}

if (-not $IsaacRoot) {
    $IsaacRoot = if ($env:ISAAC_SIM_ROOT) {
        $env:ISAAC_SIM_ROOT
    } else {
        'C:\isaac-sim\_build\windows-x86_64\release'
    }
}
if (-not $Scene) {
    $Scene = if ($SandDeformation -or $env:ROVER_SAND_DEFORMATION -eq '1') {
        Join-Path $repo 'scenes\in work\CAMERASYNCSSMOETIMES_55KG_SAND_CANDIDATE.usd'
    } elseif ($env:ROVER_SCENE) {
        $env:ROVER_SCENE
    } else {
        Join-Path $repo 'scenes\CAMERASYNCSSMOETIMES.usd'
    }
}
if (-not [IO.Path]::IsPathRooted($Scene)) {
    $Scene = Join-Path $repo $Scene
}

$kitExe = Join-Path $IsaacRoot 'kit\kit.exe'
$appKit = Join-Path $IsaacRoot 'apps\isaacsim.exp.full.kit'
if (-not (Test-Path -LiteralPath $kitExe)) {
    throw "Isaac Sim Kit executable not found: $kitExe. Set ISAAC_SIM_ROOT or pass -IsaacRoot."
}
if (-not (Test-Path -LiteralPath $appKit)) {
    throw "Isaac Sim full application definition not found: $appKit"
}
if (-not (Test-Path -LiteralPath $Scene)) {
    throw "Scene not found: $Scene"
}

$existing = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '(?i)^isaac-sim(\.exe)?$|^kit(\.exe)?$' }
if ($existing) {
    $requestedDomain = if ($env:ROS_DOMAIN_ID) { $env:ROS_DOMAIN_ID } else { '0' }
    Write-Host 'Isaac Sim/Kit is already running; leaving the open stage untouched.' -ForegroundColor Yellow
    $existing | Select-Object Name, ProcessId | Format-Table -AutoSize
    Write-Warning "The running Isaac Sim process keeps its original ROS environment. Restart it to apply ROS $RosDistro / Fast DDS / domain $requestedDomain."
    if ($SandDeformation -or $env:ROVER_SAND_DEFORMATION -eq '1') {
        Write-Warning 'Sand deformation cannot attach to an already running Isaac Sim process. Save any open scene changes, close Isaac Sim, and relaunch with -SandDeformation.'
    }
    return
}

# Prefer the bundled Humble libraries to match the Docker ROS runtime.
# Jazzy remains available for installs that do not bundle Humble.
$rosLib = Join-Path $IsaacRoot "exts\isaacsim.ros2.core\$RosDistro\lib"
if (-not (Test-Path -LiteralPath $rosLib)) {
    throw "Isaac Sim ROS 2 libraries not found for '$RosDistro': $rosLib"
}
$env:ROS_DISTRO = $RosDistro
$env:RMW_IMPLEMENTATION = 'rmw_fastrtps_cpp'
$env:ROS_DOMAIN_ID = if ($env:ROS_DOMAIN_ID) { $env:ROS_DOMAIN_ID } else { '0' }
$env:isaac_sim_package_path = $IsaacRoot
Remove-Item Env:FASTRTPS_DEFAULT_PROFILES_FILE -ErrorAction SilentlyContinue
Remove-Item Env:FASTDDS_DEFAULT_PROFILES_FILE -ErrorAction SilentlyContinue
if ((($env:PATH -split ';') | Where-Object { $_ -ieq $rosLib }).Count -eq 0) {
    $env:PATH = "$rosLib;$env:PATH"
}

$repoAlias = Join-Path $IsaacRoot '_aiaa_rover_simulation_repo'
if (Test-Path -LiteralPath $repoAlias) {
    $aliasItem = Get-Item -LiteralPath $repoAlias
    if ($aliasItem.LinkType -ne 'Junction' -or -not $aliasItem.Target) {
        throw "Refusing to use '$repoAlias'; it exists but is not a repository junction."
    }
    $resolvedAlias = [IO.Path]::GetFullPath([string]$aliasItem.Target).TrimEnd('\')
    if (-not $resolvedAlias.Equals($repo.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to use existing Isaac Sim repo alias '$repoAlias'; it resolves to '$resolvedAlias', not '$repo'."
    }
} else {
    New-Item -ItemType Junction -Path $repoAlias -Target $repo | Out-Null
}
$openSceneScript = Join-Path $repoAlias 'isaac\diagnostics\open_scene_on_start.py'
if (-not (Test-Path -LiteralPath $openSceneScript)) {
    throw "Isaac Sim stage-open helper not found through the repo alias: $openSceneScript"
}

$env:AIAA_ROVER_SCENE = $Scene
$sandEnabled = $SandDeformation -or $env:ROVER_SAND_DEFORMATION -eq '1'
$env:AIAA_ROVER_SAND_DEFORMATION = if ($sandEnabled) { '1' } else { '0' }
Write-Host "Launching Isaac Sim with ROS $RosDistro / Fast DDS / domain $env:ROS_DOMAIN_ID" -ForegroundColor Cyan
Write-Host "Opening scene: $Scene"
if ($sandEnabled) {
    Write-Host 'Wheel-driven sand deformation enabled.' -ForegroundColor Cyan
    Write-Warning 'Sand mode is experimental: live visual terrain updates currently stall powered rover travel and reduce camera output. See docs/performance-analysis.md.'
}
try {
    # Kit's --exec file parser splits paths at spaces even when quoted. The
    # no-space junction keeps the project itself in its original location.
    Start-Process -FilePath $kitExe -ArgumentList @($appKit, '--exec', "`"$openSceneScript`"") -WorkingDirectory $IsaacRoot
} finally {
    Remove-Item Env:AIAA_ROVER_SCENE -ErrorAction SilentlyContinue
    Remove-Item Env:AIAA_ROVER_SAND_DEFORMATION -ErrorAction SilentlyContinue
}
