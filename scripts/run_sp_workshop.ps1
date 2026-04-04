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

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    Invoke-PythonWithArgs @("-m", "venv", ".venv")
}

$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment is missing Python. Recreating .venv..."
    Remove-Item ".venv" -Recurse -Force -ErrorAction SilentlyContinue
    Invoke-PythonWithArgs @("-m", "venv", ".venv")
}

$marker = Join-Path $projectDir ".venv\.requirements_installed"
$requirements = Join-Path $projectDir "requirements.txt"
$needsInstall = (-not (Test-Path $marker)) -or ((Get-Item $requirements).LastWriteTime -gt (Get-Item $marker).LastWriteTime)
if ($needsInstall) {
    Write-Host "Installing requirements..."
    & $venvPython -m pip install -r requirements.txt
    New-Item -ItemType File -Path $marker -Force | Out-Null
}

Write-Host "Setup almost complete."
Write-Host ""
Write-Host "If the app doesn't start:"
Write-Host "It will tell you what's missing (FFmpeg, etc.)"
Write-Host ""
Write-Host "Starting SP Workshop..."
& $venvPython app.py
