$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonCandidates = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe")
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $pythonExe = $pythonCommand.Source
    } else {
        Write-Host ""
        Write-Host "没有找到 Python。请先按 README 创建 .venv 并安装依赖。" -ForegroundColor Red
        Write-Host ""
        Pause
        exit 1
    }
}

Start-Process powershell -ArgumentList "-NoProfile", "-Command", "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:18010'" -WindowStyle Hidden
& $pythonExe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18010
