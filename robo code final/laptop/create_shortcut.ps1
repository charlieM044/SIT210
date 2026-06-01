# Creates a Desktop shortcut that points to the built executable in dist\
$exe = Join-Path -Path (Get-Location) -ChildPath "dist\frontend.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Executable not found: $exe`nRun the build first (build_exe.bat)."
    exit 1
}

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Frontend.lnk")
$sc.TargetPath = $exe
$sc.WorkingDirectory = Split-Path $exe
$sc.IconLocation = $exe
$sc.Save()
Write-Output "Shortcut created on Desktop: Frontend.lnk"
