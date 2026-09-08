param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $Path).Path
$issues = [System.Collections.Generic.List[string]]::new()

$files = Get-ChildItem -LiteralPath $root -Recurse -File -Force |
    Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' }
foreach ($file in $files) {
    $relative = [System.IO.Path]::GetRelativePath($root, $file.FullName)
    $normalized = $relative.Replace("\", "/")
    $leaf = $file.Name

    if ($normalized -match '(^|/)(\.venv|venv|__pycache__|backups|scratch|dist)(/|$)') {
        $issues.Add("禁止目录: $normalized")
    }
    if ($leaf -match '\.(db|sqlite|sqlite3|pyc|log|tmp|bak|zip)$') {
        $issues.Add("禁止文件类型: $normalized")
    }
    if ($leaf -eq ".env" -or ($leaf -like ".env.*" -and $leaf -ne ".env.example")) {
        $issues.Add("本地配置文件: $normalized")
    }
    if ($normalized -like "data/*.json" -and $normalized -ne "data/ai_monitor.json") {
        $issues.Add("个人数据文件: $normalized")
    }
}

$textExtensions = @(".py", ".md", ".json", ".yaml", ".yml", ".ps1", ".bat", ".html", ".js", ".css", ".txt", ".example")
$secretPattern = '(?i)(sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'
$emailPattern = '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
$phonePattern = '(?<!\d)\+\d{10,15}(?!\d)'
$windowsPathPattern = '(?<![A-Za-z])[A-Za-z]:[\\/][^\r\n`"'']+'

foreach ($file in $files) {
    if ($textExtensions -notcontains $file.Extension.ToLowerInvariant() -and $file.Name -ne ".env.example" -and $file.Name -ne ".gitignore") {
        continue
    }
    $relative = [System.IO.Path]::GetRelativePath($root, $file.FullName)
    $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) { continue }

    if ($content -match $secretPattern) { $issues.Add("疑似密钥: $relative") }
    if ($content -match $emailPattern) { $issues.Add("电子邮箱: $relative") }
    if ($content -match $phonePattern) { $issues.Add("国际手机号: $relative") }
    if ($content -match $windowsPathPattern) { $issues.Add("本机绝对路径: $relative") }
}

if ($issues.Count -gt 0) {
    $issues | Sort-Object -Unique | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    throw "公开包隐私检查失败，共发现 $($issues.Count) 项。"
}

Write-Host "PUBLIC_PACKAGE_AUDIT=PASS ($($files.Count) files)" -ForegroundColor Green
