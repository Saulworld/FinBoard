"""One-time migration of the existing templates; all work stays in this copy."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
assert (ROOT / "LOCAL_EDITION.json").exists()
p = ROOT / "app/templates/base.html"
s = p.read_text(encoding="utf-8")
if "landscape-stage" in s:
    raise SystemExit("Already migrated")
# Move the valid shared script to a cacheable file and remove the accidentally duplicated JS inside CSS.
script = re.search(r"    <script>\s*([\s\S]*?)\s*</script>", s)
shared = script.group(1)
s = s[: script.start()] + s[script.end() :]
s = re.sub(r"    <style>[\s\S]*?</style>", "", s, count=1)
(ROOT / "app/static/js/shell.js").write_text(shared + "\n", encoding="utf-8")
s = s.replace("app.js?v=1.0.11", "app.js?v=2.0.0")
s = s.replace(
    "{% block head %}",
    '<script defer src="/static/js/shell.js?v=2.0.0"></script>\n    <script defer src="/static/js/glass.js?v=2.0.0"></script>\n    {% block head %}',
    1,
)
s = s.replace(
    "<body>",
    """<body class="local-glass" data-page="{{ active_page }}">
    <div class="landscape-stage" aria-hidden="true"><div class="landscape-layer landscape-a"></div><div class="landscape-layer landscape-b"></div><div class="landscape-wash"></div></div>""",
)
# Preserve every navigation URL and decorate it with a local SVG symbol.
icons = ["overview", "briefing", "holdings", "tools", "card", "phone", "spark"]
pattern = r'(<a href="[^\"]+" class="\{\{.*?active_page.*?\}\}">)([^<]+)(</a>)'
n = 0


def nav(m):
    global n
    icon = icons[n]
    n += 1
    return (
        m.group(1)
        + f'<svg class="nav-icon" aria-hidden="true"><use href="/static/images/ui-icons.svg#{icon}"></use></svg><span>'
        + m.group(2)
        + "</span>"
        + m.group(3)
    )


s = re.sub(pattern, nav, s)
assert n == 7
# Collapsible utilities preserve their existing fields, IDs and handlers.
for title in ["数据源选择", "刷新间隔"]:
    marker = "<h3>" + title + "</h3>"
    pos = s.index(marker)
    start = s.rfind('<section class="sidebar-card">', 0, pos)
    end = s.index("</section>", pos) + len("</section>")
    block = s[start:end]
    block = block.replace(
        '<section class="sidebar-card">',
        '<details class="sidebar-card sidebar-utility">',
        1,
    )
    block = block.replace(
        '<div class="sidebar-card-head">', '<summary class="sidebar-card-head">', 1
    )
    hpos = block.index("</h3>")
    first_close = block.index("</div>", hpos)
    block = block[:first_close] + "</summary>" + block[first_close + 6 :]
    block = block[:-10] + "</details>"
    s = s[:start] + block + s[end:]
pos = s.index("        </aside>")
s = (
    s[:pos]
    + """            <div class="sidebar-footer">
                <button type="button" id="sceneNext" title="切换下一幅风景">更换风景</button>
                <button type="button" id="scenePause" aria-pressed="false">暂停轮换</button>
                <a href="/local-maintenance" class="maintenance-link">备份与记录 ↗</a>
            </div>
"""
    + s[pos:]
)
s = s.replace(
    '<div class="main-shell">',
    '<div class="main-shell">\n            <div class="workspace-caption"><span>FinBoard / 本地工作台</span><span id="sceneName">远山湖泊</span></div>',
)
s = s.replace(
    '<link rel="stylesheet" href="/static/css/layout_stability.css?v=1.0.15">',
    '<link rel="stylesheet" href="/static/css/layout_stability.css?v=1.0.15">\n<link rel="stylesheet" href="/static/css/glass.css?v=2.0.0">',
)
p.write_text(s, encoding="utf-8")
# Recompose the existing dashboard sections rather than reimplementing their functionality.
p = ROOT / "app/templates/dashboard.html"
s = p.read_text(encoding="utf-8")
a = s.index('<section class="content-split">')
b = s.index('<section class="board-card">', a)
c = s.index("</section>", b) + 10
add = s[b:c].replace('class="board-card"', 'class="board-card dashboard-add"', 1)
b = s.index('<section class="board-card">', c)
c = s.index("</section>", b) + 10
indices = s[b:c].replace('class="board-card"', 'class="board-card market-card"', 1)
end = s.index("</section>", c) + 10
b = s.index('<section class="board-card">', end)
c = s.index("</section>", b) + 10
table = s[b:c].replace('class="board-card"', 'class="board-card watchlist-card"', 1)
s = (
    s[:a]
    + '<div class="dashboard-grid">\n'
    + indices
    + "\n"
    + table
    + "\n"
    + add
    + "\n</div>"
    + s[c:]
)
p.write_text(s, encoding="utf-8")
print("TEMPLATES_MIGRATED")
