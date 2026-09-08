param(
    [string]$OutputDirectory = "",
    [string]$Version = "0.1"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $desktop "FinBoard-v$Version"
}

$destination = [System.IO.Path]::GetFullPath($OutputDirectory)
$source = [System.IO.Path]::GetFullPath($projectRoot)
if ($destination.TrimEnd("\") -eq $source.TrimEnd("\") -or $destination.StartsWith($source.TrimEnd("\") + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "输出目录必须位于 FinBoard 项目目录之外。"
}
if (Test-Path -LiteralPath $destination) {
    throw "输出目录已存在，请换一个新目录: $destination"
}

function Copy-PublicTree {
    param([string]$From, [string]$To)
    Get-ChildItem -LiteralPath $From -Recurse -File -Force |
        Where-Object {
            $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and
            $_.Extension -ne ".pyc"
        } |
        ForEach-Object {
            $relative = [System.IO.Path]::GetRelativePath($From, $_.FullName)
            $target = Join-Path $To $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $target
        }
}

New-Item -ItemType Directory -Path $destination | Out-Null

foreach ($directory in @("app", "tests", ".agents", ".github", "scripts")) {
    Copy-PublicTree -From (Join-Path $source $directory) -To (Join-Path $destination $directory)
}

New-Item -ItemType Directory -Path (Join-Path $destination "docs") | Out-Null
foreach ($doc in @("AI_BRIEFING.md", "DESIGN_GUIDELINES.md", "python_codebase_guide.md", "GITHUB_PUBLISH_GUIDE.md", "PROJECT_STRUCTURE.md", "LEGAL.md", "MAINTENANCE.md")) {
    Copy-Item -LiteralPath (Join-Path $source "docs\$doc") -Destination (Join-Path $destination "docs\$doc")
}

foreach ($file in @("README.md", ".env.example", "requirements.txt", "start_local.ps1", "start_local.bat", "AGENTS.md", "LICENSE")) {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $destination $file)
}

foreach ($file in @("CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md")) {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $destination ".github\$file")
}

Copy-Item -LiteralPath (Join-Path $source "PUBLIC_CHANGELOG.md") -Destination (Join-Path $destination "CHANGELOG.md")

$publicIgnore = Get-Content -LiteralPath (Join-Path $source ".gitignore") | Where-Object { $_ -ne "/CHANGELOG.md" }
$publicIgnore | Set-Content -LiteralPath (Join-Path $destination ".gitignore") -Encoding utf8

New-Item -ItemType Directory -Path (Join-Path $destination "data") | Out-Null
Copy-Item -LiteralPath (Join-Path $source "data\README.md") -Destination (Join-Path $destination "data\README.md")
Copy-Item -LiteralPath (Join-Path $source "data\ai_monitor.json") -Destination (Join-Path $destination "data\ai_monitor.json")

& (Join-Path $destination "scripts\audit_public_package.ps1") -Path $destination

$zipPath = "$destination.zip"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($destination, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)

[pscustomobject]@{
    Directory = $destination
    Zip = $zipPath
}
