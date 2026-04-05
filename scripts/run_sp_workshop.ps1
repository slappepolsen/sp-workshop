$ErrorActionPreference = "Stop"

$projectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectDir

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try { py -3.12 -c "import sys" *> $null; return @("py", "-3.12") } catch {}
        try { py -3 -c "import sys" *> $null; return @("py", "-3") } catch {}
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python not found. Install Python 3.12 from https://www.python.org/downloads/"
}

$pythonCmd = Get-PythonCommand

function Invoke-PythonWithArgs([string[]]$extraArgs) {
    $allArgs = @()
    if ($pythonCmd.Length -gt 1) {
        $allArgs += $pythonCmd[1..($pythonCmd.Length - 1)]
    }
    $allArgs += $extraArgs
    & $pythonCmd[0] @allArgs
}

$baseDir = Join-Path $env:USERPROFILE "VideoProcessing"
$sharedVenv = Join-Path $baseDir ".venv"
$legacyVenv = Join-Path (Join-Path $env:USERPROFILE "VideoProcessingApp") ".venv"
$projectVenv = Join-Path $projectDir ".venv"

New-Item -ItemType Directory -Path $baseDir -Force | Out-Null

if (Test-Path $sharedVenv) {
    $venvDir = $sharedVenv
} elseif (Test-Path $legacyVenv) {
    $venvDir = $legacyVenv
} elseif (Test-Path $projectVenv) {
    $venvDir = $projectVenv
} else {
    $venvDir = $sharedVenv
    Write-Host "Creating virtual environment..."
    Invoke-PythonWithArgs @("-m", "venv", $venvDir)
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment is missing Python. Recreating venv..."
    Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue
    Invoke-PythonWithArgs @("-m", "venv", $venvDir)
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
}

$reqHashFile = Join-Path $venvDir ".requirements_hash"
$reqMain = Join-Path $projectDir "requirements.txt"
$reqWhisper = Join-Path $projectDir "requirements-whisper-ai.txt"

$env:SP_PROJECT_DIR = $projectDir
$hashScript = @'
import hashlib
import os
from pathlib import Path
p = Path(os.environ["SP_PROJECT_DIR"])
main = (p / "requirements.txt").read_bytes()
wh = (p / "requirements-whisper-ai.txt").read_bytes()
print(hashlib.sha256(main + wh).hexdigest())
'@

$newHash = (& $venvPython -c $hashScript).Trim()

$needsInstall = $true
if (Test-Path $reqHashFile) {
    $oldHash = (Get-Content -Path $reqHashFile -Raw).Trim()
    if ($oldHash -eq $newHash) {
        $needsInstall = $false
    }
}

if ($needsInstall) {
    Write-Host "Installing requirements..."
    & $venvPython -m pip install --upgrade pip
    # Whisper-ai first: torch only; then main (torchvision, openai-whisper, etc.)
    & $venvPython -m pip install -r $reqWhisper -r $reqMain
    [System.IO.File]::WriteAllText($reqHashFile, $newHash)
}

Write-Host "Setup almost complete."
Write-Host ""
Write-Host "If the app doesn't start:"
Write-Host "It will tell you what's missing (FFmpeg, etc.)"
Write-Host ""
Write-Host "Starting SP Workshop..."

Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:VIRTUAL_ENV = $venvDir

$venvBin = Join-Path $venvDir "Scripts"
$env:Path = "$venvBin;$env:Path"

& $venvPython (Join-Path $projectDir "app.py")
