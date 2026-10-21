from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "docs/verification"
out.mkdir(exist_ok=True)
errors = []
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(
        viewport={"width": 1680, "height": 1050}, device_scale_factor=1
    )
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:18011/", wait_until="domcontentloaded")
    page.wait_for_timeout(1300)
    page.screenshot(path=str(out / "dashboard-desktop.png"))
    checks.append({"path": "/", "title": page.locator(".page-title").inner_text()})
    for slug in [
        "daily-briefing",
        "holdings",
        "cards",
        "wallet-cards",
        "phones",
        "ai-monitor",
        "local-maintenance",
        "cards",
        "wallet-cards",
        "ai-monitor",
    ]:
        path = "/" + slug
        if slug == "local-maintenance":
            page.goto("http://127.0.0.1:18011" + path, wait_until="domcontentloaded")
        else:
            page.locator(f'a[href="{path}"]').first.click()
        page.wait_for_function("(path)=>location.pathname===path", arg=path)
        page.wait_for_timeout(850)
        checks.append({"path": path, "title": page.locator(".page-title").inner_text()})
        page.screenshot(path=str(out / (slug + "-desktop.png")))
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(500)
    page.screenshot(path=str(out / "ai-monitor-mobile.png"))
    checks.append(
        {
            "mobile_overflow": page.evaluate(
                "document.documentElement.scrollWidth>innerWidth"
            )
        }
    )
    page.locator("#sidebarToggle").click()
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "mobile-navigation.png"))
    checks.append(
        {
            "mobile_nav_visible": page.locator("#appSidebar").evaluate(
                "(e)=>e.getBoundingClientRect().x>=0"
            )
        }
    )
    browser.close()
result = {"checks": checks, "browser_errors": errors}
(out / "visual-check.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False))
