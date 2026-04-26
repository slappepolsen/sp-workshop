$ErrorActionPreference = "Stop"

$projectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectDir

# Unblock files from a downloaded zip (Zone.Identifier "mark of the web") so scripts/modules are not blocked.
# Skip project .venv trees (can be huge); shared venv under %USERPROFILE% is not under $projectDir.
Get-ChildItem -LiteralPath $projectDir -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '[\\/]\.venv[\\/]' } |
    Unblock-File -ErrorAction SilentlyContinue

function Get-RequirementsHash {
    param(
        [Parameter(Mandatory = $true)][string]$mainPath,
        [Parameter(Mandatory = $true)][string]$whisperPath
    )
    $mainBytes = [System.IO.File]::ReadAllBytes($mainPath)
    $whBytes   = [System.IO.File]::ReadAllBytes($whisperPath)
    $combined  = New-Object byte[] ($mainBytes.Length + $whBytes.Length)
    if ($mainBytes.Length -gt 0) { [Array]::Copy($mainBytes, 0, $combined, 0, $mainBytes.Length) }
    if ($whBytes.Length -gt 0) { [Array]::Copy($whBytes, 0, $combined, $mainBytes.Length, $whBytes.Length) }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($combined)
    } finally {
        $sha.Dispose()
    }
    -join ($hashBytes | ForEach-Object { $_.ToString("x2") })
}

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { return @("py", "-3.12") }
        & py -3 -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { return @("py", "-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonSrc = (Get-Command python).Source
        if ($pythonSrc -like "*\WindowsApps\*" -or $pythonSrc -like "*WindowsApps*") {
            throw "The Microsoft Store 'python' stub was found. Install Python 3.12 from https://www.python.org/downloads/ (enable Add to PATH), then run Start_SP_Workshop.bat again."
        }
        return @("python")
    }
    throw "Python not found. Install Python 3.12 from https://www.python.org/downloads/"
}

function Invoke-PythonWithArgs {
    param([string[]]$extraArgs)
    $allArgs = @()
    if ($script:pythonCmd.Length -gt 1) {
        $allArgs += $script:pythonCmd[1..($script:pythonCmd.Length - 1)]
    }
    $allArgs += $extraArgs
    & $script:pythonCmd[0] @allArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Python exited with code $LASTEXITCODE"
    }
}

try {
    $script:pythonCmd = Get-PythonCommand

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

    $newHash = $null
    try {
        $newHash = Get-RequirementsHash -mainPath $reqMain -whisperPath $reqWhisper
    } catch {
        Write-Host "Could not compute requirements hash; will install to be safe."
    }

    $needsInstall = $true
    if ($newHash) {
        if ((Test-Path $reqHashFile) -and ((Get-Content -Path $reqHashFile -Raw).Trim() -eq $newHash)) {
            $needsInstall = $false
        }
    }

    if ($needsInstall) {
        Write-Host "Installing requirements..."
        & $venvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip install --upgrade pip failed (exit $LASTEXITCODE)" }
        # Whisper-ai first: torch only; then main (torchvision, openai-whisper, etc.)
        & $venvPython -m pip install -r $reqWhisper -r $reqMain
        if ($LASTEXITCODE -ne 0) { throw "pip install requirements failed (exit $LASTEXITCODE)" }
        $hashToStore = $null
        try {
            $hashToStore = Get-RequirementsHash -mainPath $reqMain -whisperPath $reqWhisper
        } catch {
            Write-Host "Note: could not write requirements hash; next run may repeat dependency checks."
        }
        if ($hashToStore) {
            [System.IO.File]::WriteAllText($reqHashFile, $hashToStore)
        }
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
} catch {
    Write-Host ""
    Write-Host "SP Workshop setup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
