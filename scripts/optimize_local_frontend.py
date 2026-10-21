from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
assert (ROOT / "LOCAL_EDITION.json").exists()
p = ROOT / "app/static/js/app.js"
s = p.read_text(encoding="utf-8")
if "executePageScripts" in s:
    raise SystemExit("Already optimized")
s = s.replace(
    "    // Clear active timeouts/intervals from previous page\n    runPjaxCleanups();\n",
    "",
)
s = s.replace(
    '        const doc = parser.parseFromString(html, "text/html");',
    """        const doc = parser.parseFromString(html, "text/html");
        runPjaxCleanups();
        document.body.dataset.page = doc.body.dataset.page || '';
""",
    1,
)
start = s.index("        // Extract and run script tags in the new content")
end = s.index("        // Trigger watchlist/global refresh", start)
s = (
    s[:start]
    + """        // Execute external scripts in document order; avoid racing inline initialization.
        async function executePageScripts(container) {
            if (!container) return;
            for (const oldScript of Array.from(container.querySelectorAll("script"))) {
                if (navigationId !== activeNavigationId) return;
                const newScript = document.createElement("script");
                Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                newScript.async = false;
                const loaded = oldScript.src ? new Promise((resolve, reject) => {
                    newScript.onload = resolve;
                    newScript.onerror = () => reject(new Error("页面脚本加载失败"));
                }) : Promise.resolve();
                newScript.textContent = oldScript.textContent;
                oldScript.replaceWith(newScript);
                await loaded;
            }
        }
        await executePageScripts(contentArea);
        await executePageScripts(sidebarEl);
        if (navigationId !== activeNavigationId) return;
        document.querySelector('.main-shell')?.scrollTo({top: 0, behavior: 'instant'});
        document.dispatchEvent(new CustomEvent('saul:page-ready'));

"""
    + s[end:]
)
s = s.replace(
    "let quoteRefreshInFlight = false;",
    "let quoteRefreshInFlight = false;\nlet quoteController = null;",
)
s = s.replace(
    "function runPjaxCleanups() {",
    """function runPjaxCleanups() {
    if (quoteController) { quoteController.abort(); quoteController = null; }
""",
    1,
)
s = s.replace(
    "async function refreshAllQuotes() {\n",
    "async function refreshAllQuotes() {\n    if (document.hidden) return;\n",
    1,
)
s = s.replace(
    '        quoteRefreshInFlight = true;\n        const response = await fetch(`/api/quotes/batch?pairs=${encodeURIComponent(uniquePairs.join(","))}&_t=${Date.now()}`);',
    """        quoteRefreshInFlight = true;
        quoteController = new AbortController();
        const response = await fetch(`/api/quotes/batch?pairs=${encodeURIComponent(uniquePairs.join(","))}&_t=${Date.now()}`, {signal: quoteController.signal});""",
)
s = s.replace(
    "        nodes.forEach((node) => {\n            const symbol",
    "        nodes.forEach((node) => {\n            if (!node.isConnected) return;\n            const symbol",
)
s = s.replace(
    '        console.error("batch quote refresh failed", error);',
    '        if (error.name !== "AbortError") console.error("batch quote refresh failed", error);',
)
s += """\n// Background tabs do not continuously poll quotes. Resume with one current refresh.
document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshAllQuotes(); });
"""
# Escape user-supplied history fields when building markup.
s = s.replace(
    "// Analysis history list management",
    """function historyText(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
// Analysis history list management""",
    1,
)
s = (
    s.replace("${item.name}", "${historyText(item.name)}")
    .replace("${item.symbol}", "${historyText(item.symbol)}")
    .replace("${item.market}", "${historyText(item.market)}")
)
p.write_text(s, encoding="utf-8")
# Cookies are shared across ports by browsers, so use a distinct name in this edition.
for p in (ROOT / "app").rglob("*"):
    if p.is_file() and p.suffix in {".py", ".js", ".html"}:
        text = p.read_text(encoding="utf-8")
        if (
            '"preferred_provider' in text
            or "'preferred_provider" in text
            or "`preferred_provider" in text
        ):
            text = (
                text.replace('"preferred_provider', '"glass_preferred_provider')
                .replace("'preferred_provider", "'glass_preferred_provider")
                .replace("`preferred_provider", "`glass_preferred_provider")
            )
            p.write_text(text, encoding="utf-8")
print("FRONTEND_OPTIMIZED")
