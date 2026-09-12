param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path (Split-Path -Parent $projectRoot) "FinBoard"
}

$destination = [System.IO.Path]::GetFullPath($OutputDirectory)
$source = [System.IO.Path]::GetFullPath($projectRoot)
if ($destination.TrimEnd("\") -eq $source.TrimEnd("\") -or $destination.StartsWith($source.TrimEnd("\") + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "输出目录必须位于 FinBoard 私人项目目录之外。"
}
if (Test-Path -LiteralPath $destination) {
    if (-not (Test-Path -LiteralPath (Join-Path $destination ".git"))) {
        throw "现有输出目录不是FinBoard Git工作目录，已停止覆盖: $destination"
    }
    $pendingChanges = @(& git -C $destination status --porcelain)
    if ($LASTEXITCODE -ne 0) {
        throw "无法检查FinBoard Git工作目录状态: $destination"
    }
    if ($pendingChanges.Count -gt 0) {
        throw "FinBoard目录存在未提交修改，请先检查或提交后再生成脱敏副本。"
    }
}

function Copy-PublicTree {
    param(
        [string]$From,
        [string]$To,
        [switch]$IncludeAiMonitorSkill
    )
    Get-ChildItem -LiteralPath $From -Recurse -File -Force |
        Where-Object {
            $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and
            $_.FullName -notmatch '[\\/]\.agents[\\/]skills[\\/]update-finboard[\\/]' -and
            ($IncludeAiMonitorSkill -or $_.FullName -notmatch '[\\/]\.agents[\\/]skills[\\/]update-ai-monitor[\\/]') -and
            $_.Extension -ne ".pyc"
        } |
        ForEach-Object {
            $relative = [System.IO.Path]::GetRelativePath($From, $_.FullName)
            $target = Join-Path $To $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $target
        }
}

function Convert-ToPublicBrand {
    param([string]$Root)

    $textExtensions = @(".py", ".html", ".css", ".js", ".md", ".json", ".yaml", ".yml", ".txt", ".ps1", ".bat")
    $specialTextFiles = @(".gitignore", ".env.example", "LICENSE")
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)

    Get-ChildItem -LiteralPath $Root -Recurse -File -Force |
        Where-Object {
            $_.FullName -notmatch '[\\/]\.git[\\/]' -and
            (
                $textExtensions -contains $_.Extension.ToLowerInvariant() -or
                $specialTextFiles -contains $_.Name
            )
        } |
        ForEach-Object {
            $content = [System.IO.File]::ReadAllText($_.FullName)
            # Build private-only sentinels from fragments so this exporter can
            # safely sanitize a copied version of itself.
            $privateStart = "<!-- PRIVATE_" + "LOCAL_ONLY_START -->"
            $privateEnd = "<!-- PRIVATE_" + "LOCAL_ONLY_END -->"
            $privatePattern = "(?s)" +
                [System.Text.RegularExpressions.Regex]::Escape($privateStart) +
                ".*?" +
                [System.Text.RegularExpressions.Regex]::Escape($privateEnd) +
                "\s*"
            $publicContent = [System.Text.RegularExpressions.Regex]::Replace(
                $content,
                $privatePattern,
                ""
            )
            $privateBrand = "Saul" + "money"
            $publicContent = $publicContent.Replace($privateBrand, "FinBoard").Replace($privateBrand.ToLowerInvariant(), "finboard")
            if ($publicContent -ne $content) {
                [System.IO.File]::WriteAllText($_.FullName, $publicContent, $utf8NoBom)
            }
        }
}

New-Item -ItemType Directory -Path $destination -Force | Out-Null

foreach ($directory in @("app", "tests", ".agents", ".github", "scripts")) {
    Copy-PublicTree -From (Join-Path $source $directory) -To (Join-Path $destination $directory)
}

New-Item -ItemType Directory -Path (Join-Path $destination "docs") -Force | Out-Null
foreach ($doc in @("AI_BRIEFING.md", "DESIGN_GUIDELINES.md", "python_codebase_guide.md", "GITHUB_PUBLISH_GUIDE.md", "PROJECT_STRUCTURE.md", "LEGAL.md", "MAINTENANCE.md", "UPLOAD_HISTORY.md")) {
    Copy-Item -LiteralPath (Join-Path $source "docs\$doc") -Destination (Join-Path $destination "docs\$doc")
}
if (Test-Path -LiteralPath (Join-Path $source "docs\images")) {
    Copy-PublicTree -From (Join-Path $source "docs\images") -To (Join-Path $destination "docs\images")
}

# Keep the reusable AI-monitor Skill as a non-auto-registered public attachment.
# A public checkout can therefore export itself without requiring the private
# project's automatic-discovery path.
$aiSkillSource = Join-Path $source ".agents\skills\update-ai-monitor"
if (-not (Test-Path -LiteralPath $aiSkillSource)) {
    $aiSkillSource = Join-Path $source "docs\skills\update-ai-monitor"
}
if (-not (Test-Path -LiteralPath $aiSkillSource)) {
    throw "缺少update-ai-monitor Skill公开附件。"
}
Copy-PublicTree `
    -From $aiSkillSource `
    -To (Join-Path $destination "docs\skills\update-ai-monitor") `
    -IncludeAiMonitorSkill

foreach ($file in @("README.md", ".env.example", "requirements.txt", "start_local.ps1", "start_local.bat", "AGENTS.md", "LICENSE")) {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $destination $file)
}

$publicChangelogSource = Join-Path $source "docs\publishing\CHANGELOG.md"
if (-not (Test-Path -LiteralPath $publicChangelogSource)) {
    $publicChangelogSource = Join-Path $source "CHANGELOG.md"
}
if (-not (Test-Path -LiteralPath $publicChangelogSource)) {
    throw "缺少公开CHANGELOG.md。"
}
Copy-Item -LiteralPath $publicChangelogSource -Destination (Join-Path $destination "CHANGELOG.md")

$publicIgnore = Get-Content -LiteralPath (Join-Path $source ".gitignore") | Where-Object { $_ -ne "/CHANGELOG.md" }
$publicIgnore | Set-Content -LiteralPath (Join-Path $destination ".gitignore") -Encoding utf8

New-Item -ItemType Directory -Path (Join-Path $destination "data") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source "data\README.md") -Destination (Join-Path $destination "data\README.md")
Copy-Item -LiteralPath (Join-Path $source "data\ai_monitor.json") -Destination (Join-Path $destination "data\ai_monitor.json")

Convert-ToPublicBrand -Root $destination

& (Join-Path $destination "scripts\audit_public_package.ps1") -Path $destination

[pscustomobject]@{
    Directory = $destination
}
