param(
    [string]$ProjectRoot = "D:\kniacknack_post",
    [string]$WslDistro = "Ubuntu-24.04",
    [string]$ComposeDir = "~/rsshub",
    [string]$DockerDesktopPath = "",
    [int]$DockerDesktopStartTimeoutSec = 180,
    [int]$ComposeWarmupSec = 20,
    [int]$PollIntervalSec = 3
)

$ErrorActionPreference = "Stop"
$dockerDesktopStartedByScript = $false

$pythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$entryScript = Join-Path $ProjectRoot "post\knicknack_post.py"
$workingDir = Join-Path $ProjectRoot "post"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

if (-not (Test-Path $entryScript)) {
    throw "Entry script not found: $entryScript"
}

function Invoke-WslSh {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $previousNativePreference = $PSNativeCommandUseErrorActionPreference
    $ErrorActionPreference = "Continue"
    $PSNativeCommandUseErrorActionPreference = $false

    try {
        $output = & wsl.exe -d $WslDistro -- sh -lc $Command 2>&1 | ForEach-Object { "$_" }
        $exitCode = $LASTEXITCODE
        return [pscustomobject]@{
            Output = ($output | Out-String).Trim()
            ExitCode = $exitCode
        }
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $previousNativePreference
    }
}

function Test-DockerReadyInWsl {
    $result = Invoke-WslSh -Command "docker info >/dev/null 2>&1"
    return $result.ExitCode -eq 0
}

function Get-DockerDesktopExecutable {
    if ($DockerDesktopPath -and (Test-Path $DockerDesktopPath)) {
        return $DockerDesktopPath
    }

    $candidates = @(
        "C:\Program Files\Docker\Docker\Docker Desktop.exe",
        "C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

function Ensure-DockerDesktopReady {
    if (Test-DockerReadyInWsl) {
        return $false
    }

    $dockerDesktopExe = Get-DockerDesktopExecutable
    if (-not $dockerDesktopExe) {
        throw "Docker Desktop executable not found, and Docker is not ready in WSL."
    }

    Start-Process -FilePath $dockerDesktopExe -WindowStyle Hidden

    $deadline = (Get-Date).AddSeconds($DockerDesktopStartTimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerReadyInWsl) {
            return $true
        }
        Start-Sleep -Seconds $PollIntervalSec
    }

    throw "Docker Desktop did not become ready within $DockerDesktopStartTimeoutSec seconds."
}

function Stop-DockerDesktopIfStarted {
    if (-not $dockerDesktopStartedByScript) {
        return
    }

    $processNames = @("Docker Desktop", "Docker Desktop Backend", "com.docker.backend", "com.docker.proxy")
    foreach ($processName in $processNames) {
        Get-Process -Name $processName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComposeCommand
    )

    $fullCommand = "cd -- $ComposeDir && docker compose $ComposeCommand"
    return Invoke-WslSh -Command $fullCommand
}

function Test-ComposeProjectExists {
    $result = Invoke-WslSh -Command "cd -- $ComposeDir && test -f docker-compose.yml"
    return $result.ExitCode -eq 0
}

if (-not (Test-ComposeProjectExists)) {
    throw "docker-compose.yml not found in WSL directory: $ComposeDir"
}

try {
    $dockerDesktopStartedByScript = Ensure-DockerDesktopReady

    $upResult = Invoke-Compose "up -d"
    if ($upResult.ExitCode -ne 0) {
        throw "Failed to start docker compose services. $($upResult.Output)"
    }

    Start-Sleep -Seconds $ComposeWarmupSec

    Push-Location $workingDir
    try {
        & $pythonExe $entryScript
        if ($LASTEXITCODE -ne 0) {
            throw "knicknack_post exited with code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    $downResult = Invoke-Compose "down"
    if ($downResult.ExitCode -ne 0) {
        Write-Error "Failed to stop docker compose services in '$ComposeDir'. $($downResult.Output)"
    }

    Stop-DockerDesktopIfStarted
}
