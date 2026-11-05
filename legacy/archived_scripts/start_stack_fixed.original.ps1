# Start Isaac Sim and optional AI services with compatible ROS middleware.
# Windows PowerShell 5.1 / Isaac Sim 6.1.0.
[CmdletBinding()]
param(
    [switch]$SkipAI,
    [switch]$SkipIsaac,
    [ValidateSet('humble','jazzy')][string]$RosDistro = 'humble',
    [switch]$KeepOriginalRosEnvironment
)
$ErrorActionPreference = 'Stop'
$isaacRepo = 'C:\Users\AIAA UT Dallas\Documents\Aerobotics\isaacsim-mcp-server'
$isaacInstall = 'C:\isaac-sim\_build\windows-x86_64\release'
$llamaDir = 'C:\Users\AIAA UT Dallas\Documents\llama.cpp\build\bin\Release'
$modelPath = 'C:\Users\AIAA UT Dallas\.lmstudio\models\lmstudio-community\gemma-4-E4B-it-GGUF\gemma-4-E4B-it-Q4_K_M.gguf'
function Require-Path([string]$path, [string]$description) {
    if (-not (Test-Path -LiteralPath $path)) { throw "$description missing: $path" }
}
Require-Path $isaacRepo 'Isaac integration repository'
if (-not $KeepOriginalRosEnvironment) {
    # Fast DDS matches Humble/Fast DDS in cometbot_dev; Zenoh and Fast DDS do not discover each other directly.
    # Use a bundled ROS library directory only if it actually exists.
    $libDir = Join-Path $isaacInstall "exts\isaacsim.ros2.core\$RosDistro\lib"
    if (-not (Test-Path -LiteralPath $libDir)) {
        Write-Warning "Bundled $RosDistro libraries not found: $libDir"
        if ($RosDistro -eq 'humble') {
            $RosDistro = 'jazzy'
            $libDir = Join-Path $isaacInstall 'exts\isaacsim.ros2.core\jazzy\lib'
            Write-Warning 'Trying bundled Jazzy with Fast DDS; ROS 2 topic/message compatibility must still be verified.'
        }
    }
    if (-not (Test-Path -LiteralPath $libDir)) { throw "No ROS 2 Fast DDS bundle detected at $libDir. Use -KeepOriginalRosEnvironment only for diagnostics." }
    $env:ROS_DISTRO = $RosDistro
    $env:RMW_IMPLEMENTATION = 'rmw_fastrtps_cpp'
    $env:ROS_DOMAIN_ID = '0'
    $env:isaac_sim_package_path = $isaacInstall
    Remove-Item Env:FASTRTPS_DEFAULT_PROFILES_FILE -ErrorAction SilentlyContinue
    Remove-Item Env:FASTDDS_DEFAULT_PROFILES_FILE -ErrorAction SilentlyContinue
    if ((($env:PATH -split ';') | Where-Object { $_ -ieq $libDir }).Count -eq 0) {
        $env:PATH = "$libDir;$env:PATH"
    }
    Write-Host "Isaac ROS: $RosDistro / Fast DDS / domain 0" -ForegroundColor Cyan
    Write-Warning 'This sets compatible middleware, but does not yet configure UDP discovery across Windows and WSL.'
}
if (-not $SkipAI) {
    $gitBash = 'C:\Program Files\Git\bin\bash.exe'
    $mcpScript = Join-Path $isaacRepo 'scripts\run_mcp_server.sh'
    $llamaExe = Join-Path $llamaDir 'llama-server.exe'
    Require-Path $gitBash 'Git Bash'
    Require-Path $mcpScript 'MCP server startup script'
    Require-Path $llamaExe 'Local model executable'
    Require-Path $modelPath 'Local model GGUF'
    Start-Process -FilePath $gitBash -WorkingDirectory $isaacRepo -ArgumentList '-lc "./scripts/run_mcp_server.sh; exec bash"' | Out-Null
    Start-Sleep -Seconds 3
    $cmd = '"' + $llamaExe + '" -m "' + $modelPath + '" -ngl 99 --webui-mcp-proxy'
    Start-Process -FilePath 'cmd.exe' -WorkingDirectory $llamaDir -ArgumentList ('/k "' + $cmd + '"') | Out-Null
}
if (-not $SkipIsaac) {
    $bat = Join-Path $isaacRepo 'scripts\run_isaac_sim.bat'
    Require-Path $bat 'Isaac Sim launcher'
    # Windows child processes inherit the ROS environment set above.
    # Keep the team's extension/MCP loader (rather than bypassing with a stock launch).
    Write-Host 'Launching Isaac Sim via team script...' -ForegroundColor Cyan
    Start-Process -FilePath 'cmd.exe' -WorkingDirectory $isaacRepo -ArgumentList ('/k ""' + $bat + '""') | Out-Null
}
Write-Host 'Isaac launcher dispatched. Verify ROS_DISTRO/RMW in Isaac Python Script Editor.'
