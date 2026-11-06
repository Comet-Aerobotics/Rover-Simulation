[CmdletBinding()]
param(
    [ValidateSet('Diagnostics', 'Start')]
    [string]$Mode = 'Start',
    [switch]$SandDeformation
)

$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'start_rover.ps1'
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Supported rover launcher not found: $launcher"
}

& $launcher -Mode $Mode -SandDeformation:$SandDeformation
