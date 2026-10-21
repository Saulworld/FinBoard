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
            $publicContent = $publicContent.Replace($privateBrand, "FinBoard").Replace($privateBrand.ToLowerInvariant(), "finboard").Replace("FINBOARD_", "FINBOARD_")
            if ($publicContent -ne $content) {
                [System.IO.File]::WriteAllText($_.FullName, $publicContent, $utf8NoBom)
            }
        }
}

New-Item -ItemType Directory -Path $destination -Force | Out-Null

foreach ($directory in @("app", "tests", ".agents", ".github", "scripts")) {
    Copy-PublicTree -From (Join-Path $source $directory) -To (Join-Path $destination $directory)
}

# Personal address suggestions belong to the private data set. Keep the
# shared address-entry behavior while shipping an empty public suggestion list.
$publicDocumentsRouter = Join-Path $destination "app\routers\overseas_documents.py"
$documentsSource = [System.IO.File]::ReadAllText($publicDocumentsRouter)
$privateAddressBlock = '(?s)ADDRESS_OPTIONS = \[.*?\]\s*(?=def _load\()'
if (-not [System.Text.RegularExpressions.Regex]::IsMatch($documentsSource, $privateAddressBlock)) {
    throw "无法定位境外证件私人地址默认值，已停止公开导出。"
}
$documentsPublic = [System.Text.RegularExpressions.Regex]::Replace(
    $documentsSource, $privateAddressBlock, "ADDRESS_OPTIONS = []`n`n`n"
)
[System.IO.File]::WriteAllText($publicDocumentsRouter, $documentsPublic, [System.Text.UTF8Encoding]::new($false))

New-Item -ItemType Directory -Path (Join-Path $destination "docs") -Force | Out-Null
foreach ($doc in @("AI_BRIEFING.md", "DESIGN_GUIDELINES.md", "python_codebase_guide.md", "GITHUB_PUBLISH_GUIDE.md", "PROJECT_STRUCTURE.md", "LEGAL.md", "MAINTENANCE.md", "UPLOAD_HISTORY.md", "VERSION")) {
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
$publicAiSkillPath = Join-Path $destination "docs\skills\update-ai-monitor\SKILL.md"
$publicAiSkill = [System.IO.File]::ReadAllText($publicAiSkillPath)
$publicAiSkill = [System.Text.RegularExpressions.Regex]::Replace(
    $publicAiSkill,
    "新版已迁回[^，。]+，后续直接维护此主项目",
    "以当前项目目录为唯一维护入口"
)
[System.IO.File]::WriteAllText($publicAiSkillPath, $publicAiSkill, [System.Text.UTF8Encoding]::new($false))

foreach ($file in @(".env.example", "requirements.txt", "requirements-local.lock.txt", "start_local.ps1", "start_local.bat", "LICENSE")) {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $destination $file)
}
$publicAgentsSource = Join-Path $source "docs\publishing\AGENTS_PUBLIC.md"
if (-not (Test-Path -LiteralPath $publicAgentsSource)) { $publicAgentsSource = Join-Path $source "AGENTS.md" }
$publicRulesSource = Join-Path $source "docs\publishing\AGENT_RULES_PUBLIC.md"
if (-not (Test-Path -LiteralPath $publicRulesSource)) { $publicRulesSource = Join-Path $source ".agents\AGENTS.md" }
Copy-Item -LiteralPath $publicAgentsSource -Destination (Join-Path $destination "AGENTS.md")
Copy-Item -LiteralPath $publicRulesSource -Destination (Join-Path $destination ".agents\AGENTS.md")

$publicReadmeSource = Join-Path $source "docs\publishing\README.md"
if (-not (Test-Path -LiteralPath $publicReadmeSource)) {
    $publicReadmeSource = Join-Path $source "README.md"
}
Copy-Item -LiteralPath $publicReadmeSource -Destination (Join-Path $destination "README.md")

# The public launcher uses the same guarded local runtime, with a portable
# sentinel in place of the private migration source path.
$publicMarker = [ordered]@{
    edition = "local-glass"
    source_root = "/__finboard_protected_source__"
    default_port = 18011
    data_policy = "public-empty-first-run"
} | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $destination "LOCAL_EDITION.json"), $publicMarker, [System.Text.UTF8Encoding]::new($false))

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
