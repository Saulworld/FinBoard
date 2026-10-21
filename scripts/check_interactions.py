"""Browser interactions run on a temporary database copy at a separate test port."""

from pathlib import Path
import json, os, secrets, shutil, subprocess, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "docs/verification"
checks = []
errors = []
with tempfile.TemporaryDirectory(
    prefix="browser-data-", dir=ROOT / ".runtime"
) as temporary:
    for p in (ROOT / "data").iterdir():
        if p.is_file():
            shutil.copy2(p, Path(temporary) / p.name)
    env = dict(os.environ)
    env["FINBOARD_LOCAL_DATA_DIR"] = temporary
    env["PYTHONUTF8"] = "1"
    stop_token = secrets.token_urlsafe(32)
    env["FINBOARD_LOCAL_STOP_TOKEN"] = stop_token
    env.pop("DATABASE_URL", None)
    with (ROOT / ".runtime/browser-server.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [
                str(ROOT / ".venv/Scripts/python.exe"),
                "-c",
                "import uvicorn; from app.main import app; "
                "server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=18012,access_log=False)); "
                "app.state.local_server=server; server.run()",
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            for _ in range(80):
                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:18012/api/local/health", timeout=0.4
                    ) as r:
                        if json.load(r)["status"] == "ok":
                            break
                except Exception:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Temporary test server did not start")
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1600, "height": 1000})
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(
                    "http://127.0.0.1:18012/phones", wait_until="domcontentloaded"
                )
                page.locator("#togglePhoneAddForm").click()
                form = page.locator("#phoneAddForm")
                expect(form).to_be_visible()
                form.locator("[name=name]").fill("UI_AUDIT_ONLY")
                form.locator("[name=phone]").fill("+" + "44" + "00000000000")
                form.locator("[name=country]").select_option(label="德国")
                page.locator("#addPhoneRenewal").fill("KEEP_RENEWAL")
                page.locator("#addPhoneRecharge").fill("2026-09-22")
                page.locator("#addPhoneInterval").select_option("30")
                expect(page.locator("#addPhoneExpiry")).to_have_value("2026-10-22")
                expect(page.locator("#addPhoneRenewal")).to_have_value("KEEP_RENEWAL")
                form.locator("button[type=submit]").click()
                page.wait_for_url("**/phones?**")
                page.locator("#phonesSearchInput").fill("UI_AUDIT_ONLY")
                expect(page.locator("#phonesTable tbody tr:visible")).to_have_count(1)
                page.locator(".edit-phone-btn:visible").click()
                expect(page.locator("#editPhoneModal")).to_be_visible()
                page.locator("#editPhoneName").fill("UI_AUDIT_EDITED")
                page.locator("#editPhoneForm button[type=submit]").click()
                expect(page.locator("#editPhoneModal")).not_to_be_visible()
                page.locator("#phonesSearchInput").fill("UI_AUDIT_EDITED")
                expect(page.locator("#phonesTable tbody tr:visible")).to_have_count(1)
                page.locator(".delete-phone-btn:visible").click()
                expect(page.locator("#deletePhoneModal")).to_be_visible()
                page.locator("#deletePhoneModal button").filter(
                    has_text="确认删除"
                ).click()
                expect(page.locator("#deletePhoneModal")).not_to_be_visible()
                page.locator("#phonesSearchInput").fill("UI_AUDIT_EDITED")
                expect(page.locator("#phonesTable tbody tr:visible")).to_have_count(0)
                checks.append(
                    "phone add/edit/delete, date arithmetic, renewal retained, search"
                )

                page.locator('.sidebar-nav a[href="/wallet-cards"]').click()
                page.wait_for_url("**/wallet-cards")
                page.locator("#walletCardGrid .wallet-card-tile").first.click()
                expect(page.locator("#walletCardDetailModal")).to_be_visible()
                page.keyboard.press("Escape")
                expect(page.locator("#walletCardDetailModal")).not_to_be_visible()
                page.locator("#toggleWalletCardForm").click()
                expect(page.locator("#walletCardAddForm")).to_be_visible()
                page.locator("#toggleWalletCardForm").click()
                expect(page.locator("#walletCardAddForm")).not_to_be_visible()
                checks.append("wallet detail/close and collapsed add form")

                page.locator('.sidebar-nav a[href="/daily-briefing"]').click()
                page.wait_for_url("**/daily-briefing")
                expect(page.locator("#stock-card-modal-overlay")).to_have_count(1)
                page.locator(".briefing-item-card:visible").first.click()
                expect(page.locator("#stock-card-modal-overlay")).to_be_visible()
                page.keyboard.press("Escape")
                expect(page.locator("#stock-card-modal-overlay")).not_to_be_visible()
                page.locator(".sidebar-tabs .tab-btn").filter(
                    has_text="简报文件"
                ).click()
                expect(page.locator("#report-tab")).to_be_visible()
                expect(page.locator(".report-view-item:visible").first).to_be_visible()
                checks.append("single report dialog and briefing tabs")

                page.locator('.sidebar-nav a[href="/ai-monitor"]').click()
                page.wait_for_url("**/ai-monitor")
                page.locator("[data-ai-tab=plans]").click()
                expect(page.locator("[data-ai-panel=plans]")).to_be_visible()
                page.locator("[data-ai-tab=api]").click()
                page.locator("#aiModelSearch").fill("OpenAI")
                expect(page.locator("tr[data-model-row]:visible")).to_have_count(1)
                page.locator("#aiModelSearch").fill("")
                checks.append("AI model search and pricing tabs")

                page.locator('.sidebar-nav a[href="/"]').click()
                page.wait_for_url("http://127.0.0.1:18012/")
                page.evaluate("window.auditContent=document.querySelector('.content-area'); window.auditMarket=document.querySelector('.market-card')")
                watch_form = page.locator('.dashboard-add form')
                watch_form.locator('[name=symbol]').fill('UIQA')
                watch_form.locator('[name=name]').fill('UI_AUDIT_WATCH')
                watch_form.locator('[type=submit]').click()
                expect(page.locator('.remove-watchlist-btn[data-symbol="UIQA"]')).to_be_visible()
                assert page.evaluate("auditContent===document.querySelector('.content-area') && auditMarket===document.querySelector('.market-card')")
                expect(page.locator('#watchlistTable tbody tr:visible')).to_have_count(5)
                region = page.locator('#watchlistTable').locator('..')
                assert region.evaluate('(e)=>e.scrollHeight<=e.clientHeight+1')
                full_height = region.bounding_box()['height']
                page.locator('.watchlist-card .page-btn').filter(has_text='下一页').click()
                assert abs(region.bounding_box()['height']-full_height) < 2
                page.locator('.watchlist-card .page-btn').filter(has_text='上一页').click()
                page.locator('.remove-watchlist-btn[data-symbol="UIQA"]').click()
                page.locator('#removeWatchlistForm [type=submit]').click()
                expect(page.locator('.remove-watchlist-btn[data-symbol="UIQA"]')).to_have_count(0)
                assert page.evaluate("auditContent===document.querySelector('.content-area') && auditMarket===document.querySelector('.market-card')")
                checks.append('watchlist add/delete updates only list; five full rows and stable last page')

                page.evaluate(
                    "navigateTo('/cards');navigateTo('/phones');navigateTo('/holdings')"
                )
                page.wait_for_url("**/holdings")
                expect(page.locator(".page-title")).to_have_text("持仓记录")
                expect(page.locator("#portfolio-base-currency")).to_be_visible()
                checks.append(
                    "rapid navigation keeps last destination and page actions"
                )
                page.locator('.sidebar-nav a[href="/"]').click()
                page.wait_for_url("http://127.0.0.1:18012/")
                page.wait_for_timeout(700)
                old_scene = page.locator("body").get_attribute("data-scene")
                page.wait_for_function(
                    "(old)=>document.body.dataset.scene!==old",
                    arg=old_scene,
                    timeout=24000,
                )
                page.wait_for_timeout(2600)
                expect(page.locator("#scenePause, #sceneNext, .maintenance-link")).to_have_count(0)
                checks.append(
                    "automatic landscape rotation and crossfade without manual controls"
                )
                page.screenshot(path=str(out / "final-dashboard-desktop.png"))
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_timeout(400)
                assert not page.evaluate(
                    "document.documentElement.scrollWidth>innerWidth"
                )
                page.screenshot(path=str(out / "final-dashboard-mobile.png"))
                checks.append("mobile layout has no page overflow")
                assert not errors, errors
                browser.close()
        finally:
            if proc.poll() is None:
                try:
                    req = urllib.request.Request(
                        "http://127.0.0.1:18012/api/local/stop",
                        data=b"",
                        method="POST",
                        headers={"X-Local-Token": stop_token},
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        json.load(response)
                    proc.wait(timeout=20)
                except Exception:
                    proc.terminate()
                    proc.wait(timeout=15)
result = {"result": "PASS", "checks": checks, "browser_errors": errors}
(out / "interactions.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False))
