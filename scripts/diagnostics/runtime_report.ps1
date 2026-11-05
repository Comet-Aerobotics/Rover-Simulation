$ErrorActionPreference='Continue'
$distro='Ubuntu'
Write-Output "UTC: $([DateTime]::UtcNow.ToString('o'))"
Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'isaac|kit'} | Select-Object Name,ProcessId,CommandLine
wsl.exe --list --verbose
wsl.exe -d $distro --exec bash -lc 'docker context show; docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
usbipd.exe list
wsl.exe -d $distro --exec sh -lc 'ls -l /dev/input/js* /dev/input/event* 2>/dev/null || true'
