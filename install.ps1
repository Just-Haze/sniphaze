<#
.SYNOPSIS
    Installs SnipHaze and starts it. It starts with Windows from then on.
.DESCRIPTION
    SnipHaze waits for its shortcut (Ctrl+Alt+S by default) using no CPU, then
    opens Snipping Tool's overlay and adds the shadow backdrop to the snip.
.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -Hotkey "CTRL+ALT+G"
.EXAMPLE
    .\install.ps1 -Uninstall
#>
param(
    [string]$Hotkey = "CTRL+ALT+S",
    [switch]$Uninstall
)
$ErrorActionPreference = "Stop"

$Hotkey = $Hotkey -replace '\s', ''   # "CTRL + ALT + S" -> "CTRL+ALT+S"
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "SnipHaze.lnk"
$script = Join-Path $PSScriptRoot "SnipHaze.pyw"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python 3.10+ is required: https://www.python.org/downloads/" }
$exe = (& python -c "import sys; print(sys.executable)").Trim()
$pythonw = Join-Path (Split-Path $exe) "pythonw.exe"
if (-not (Test-Path $pythonw)) { throw "pythonw.exe wasn't found next to $exe" }

if ($Uninstall) {
    & $exe $script --quit
    if (Test-Path $lnk) { Remove-Item $lnk }
    Write-Output "SnipHaze stopped and removed. Your screenshots and the Originals folder are untouched."
    return
}

& $exe -c "import importlib.util, sys; sys.exit(importlib.util.find_spec('PIL') is None)"
if ($LASTEXITCODE -ne 0) {
    Write-Output "Installing Pillow..."
    & $exe -m pip install --user --quiet -r (Join-Path $PSScriptRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Couldn't install Pillow. Run: python -m pip install pillow" }
}
$why = & $exe $script --check --hotkey $Hotkey
if ($LASTEXITCODE -ne 0) { throw "Can't use the shortcut '$Hotkey': $why. Try something like CTRL+ALT+S or CTRL+SHIFT+F9." }

# Stop the running copy (if any); --quit waits until it has let go of the shortcut.
& $exe $script --quit

$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = $pythonw
$s.Arguments = "`"$script`" --hotkey $Hotkey"
$s.WorkingDirectory = $PSScriptRoot
$s.Description = "SnipHaze: snips with a macOS-style shadow backdrop"
$s.Save()

Start-Process -FilePath $pythonw -ArgumentList "`"$script`"", "--hotkey", $Hotkey -WorkingDirectory $PSScriptRoot
Write-Output "SnipHaze is running and starts with Windows. Press $Hotkey to snip."
