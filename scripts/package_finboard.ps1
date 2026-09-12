param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if ((Split-Path -Leaf $projectRoot) -ne "FinBoard" -or -not (Test-Path -LiteralPath (Join-Path $projectRoot ".git"))) {
    throw "此脚本只能在FinBoard Git工作目录中运行。"
}

$readme = [System.IO.File]::ReadAllText((Join-Path $projectRoot "README.md"))
if (-not $Version) {
    $match = [System.Text.RegularExpressions.Regex]::Match($readme, "当前版本：([0-9]+(?:\.[0-9]+)+)")
    if (-not $match.Success) {
        throw "README.md中没有找到当前版本号。"
    }
    $Version = $match.Groups[1].Value
}
if ($Version -notmatch '^[0-9]+(?:\.[0-9]+)+$') {
    throw "版本号格式无效: $Version"
}
if ($readme -notmatch "当前版本：$([System.Text.RegularExpressions.Regex]::Escape($Version))") {
    throw "README.md当前版本与打包版本不一致。"
}

$changelog = [System.IO.File]::ReadAllText((Join-Path $projectRoot "CHANGELOG.md"))
if ($changelog -notmatch "\[$([System.Text.RegularExpressions.Regex]::Escape($Version))\]") {
    throw "CHANGELOG.md中没有版本$Version的记录。"
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "docs\UPLOAD_HISTORY.md"))) {
    throw "缺少docs/UPLOAD_HISTORY.md上传时间记录。"
}

& (Join-Path $projectRoot "scripts\audit_public_package.ps1") -Path $projectRoot

$candidates = @(& git -C $projectRoot ls-files --cached --others --exclude-standard)
if ($LASTEXITCODE -ne 0 -or $candidates.Count -eq 0) {
    throw "无法取得FinBoard待打包文件列表。"
}
$files = @($candidates | Where-Object {
    Test-Path -LiteralPath (Join-Path $projectRoot $_) -PathType Leaf
})
if ($files.Count -eq 0) {
    throw "FinBoard没有可打包文件。"
}

$zipPath = Join-Path (Split-Path -Parent $projectRoot) "FinBoard-v$Version.zip"
if (Test-Path -LiteralPath $zipPath) {
    [System.IO.File]::Delete($zipPath)
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($relative in $files) {
        $fullPath = Join-Path $projectRoot $relative
        if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
            $entryName = $relative.Replace("\", "/")
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $fullPath,
                $entryName,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
}
finally {
    $archive.Dispose()
}

[pscustomobject]@{
    Version = $Version
    Package = $zipPath
    Files = $files.Count
}
