param([ValidateSet("start","backup","restore","stop")][string]$Action = "start", [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "正在准备新版独立运行环境…"
    & python -m venv (Join-Path $projectRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "创建运行环境失败。" }
    & $pythonExe -m pip install -r (Join-Path $projectRoot "requirements-local.lock.txt")
    if ($LASTEXITCODE -ne 0) { throw "安装依赖失败。" }
}
if ($Action -eq "start") {
    $runArgs = @((Join-Path $projectRoot "scripts\run_local.py"))
    if ($NoBrowser) { $runArgs += "--no-browser" }
    & $pythonExe @runArgs
} else {
    & $pythonExe (Join-Path $projectRoot "scripts\local_actions.py") $Action
}
exit $LASTEXITCODE
