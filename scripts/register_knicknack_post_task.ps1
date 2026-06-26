param(
    [string]$ProjectRoot = "D:\kniacknack_post",
    [string]$TaskName = "KnicknackPost",
    [string]$WslDistro = "Ubuntu-24.04",
    [string]$ComposeDir = "~/rsshub"
)

$ErrorActionPreference = "Stop"

$runnerScript = Join-Path $ProjectRoot "scripts\run_knicknack_post.ps1"
if (-not (Test-Path $runnerScript)) {
    throw "Runner script not found: $runnerScript"
}

$escapedRunner = $runnerScript.Replace('"', '\"')
$escapedRoot = $ProjectRoot.Replace('"', '\"')
$escapedDistro = $WslDistro.Replace('"', '\"')
$escapedComposeDir = $ComposeDir.Replace('"', '\"')

$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$escapedRunner`" -ProjectRoot `"$escapedRoot`" -WslDistro `"$escapedDistro`" -ComposeDir `"$escapedComposeDir`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $ProjectRoot
$triggerMorning = New-ScheduledTaskTrigger -Daily -At 7:30AM
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggerMorning `
    -Settings $settings `
    -Description "Run knicknack_post daily at 07:30, starting and stopping a WSL Docker container around execution." `
    -Force
