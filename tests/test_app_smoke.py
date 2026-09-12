import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func

from app.db import SessionLocal
from app.main import app
from app.models import DailyReport
from app.routers.briefing import _find_stock_card_html


class AppSmokeTests(unittest.TestCase):
    def test_main_pages_render(self):
        with TestClient(app) as client:
            for path in ("/", "/holdings", "/cards", "/wallet-cards", "/phones", "/ai-monitor"):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, f"{path}: {response.text[:300]}")

    def test_ai_monitor_has_models_and_plan_switcher(self):
        with TestClient(app) as client:
            response = client.get("/ai-monitor")
            self.assertEqual(response.status_code, 200)
            for marker in (
                'data-ai-tab="api"', 'data-ai-tab="plans"', 'data-plan-select', 'data-model-select',
                'id="aiUpdatesPagination"', "const updatesPerPage = 5",
                "ChatGPT Pro 5x", "ChatGPT Pro 20x", "ChatGPT Business Premium",
                "Claude Max 20x", "Google AI Ultra 20x", "SuperGrok Plus",
                "Token Plan Pro", "Token Plan 共享用量包", "GLM Coding Max", "Andante", "Vivace",
                "GPT-5.6 Sol", "GPT-5.6 Luna", "Claude Fable 5.1", "Claude Haiku 4.5",
                "Gemini 3.5 Flash-Lite", "Gemini 3.1 Pro Preview", "Grok Build 0.1",
                "Grok 4.20 Multi-Agent", "DeepSeek V4 Pro", "Qwen3.7 Plus", "Qwen3.8 Flash",
                "GLM-5.2", "GLM-5 Turbo", "GLM-4.5 Air", "Kimi K2.7 Code", "Kimi K2.6",
                "Muse Spark 1.3", "Muse Spark 1.2", "Muse Spark 1.1", "Muse Glimmer", "Meta Model API",
                "function updateModelRow(row)",
            ):
                self.assertIn(marker, response.text)
            self.assertEqual(response.text.count(' data-plan-card>'), 9)
            self.assertEqual(response.text.count('<tr data-model-row'), 9)
            self.assertEqual(response.text.count('<select class="ai-model-select" data-model-select'), 9)
            self.assertEqual(response.text.count('data-price='), 67)
            self.assertIn("按量计费", response.text)
            self.assertNotIn("ai-count-badge", response.text)
            self.assertNotIn("种套餐", response.text)
            self.assertNotIn("40种", response.text)
            self.assertNotIn("选择厂商套餐即可查看对应价格", response.text)

        project_root = Path(__file__).resolve().parents[1]
        style = (project_root / "app/static/css/ai_monitor.css").read_text(encoding="utf-8")
        self.assertIn("min-height: 300px", style)
        self.assertIn("min-height: 60px", style)
        self.assertIn(".ai-calculator-card { display: flex; flex-direction: column; }", style)
        self.assertIn(".ai-model-select", style)
        self.assertIn('/static/css/ai_monitor.css?v=', response.text)

        ai_data = json.loads((project_root / "data/ai_monitor.json").read_text(encoding="utf-8"))
        self.assertEqual(len(ai_data["plans"]), 67)
        plans_by_key = {
            (plan["provider"], plan["plan"]): plan
            for plan in ai_data["plans"]
        }
        expected_plan_values = {
            ("OpenAI", "ChatGPT Pro 5x"): (100, "/月", "用量为Plus的5倍"),
            ("OpenAI", "ChatGPT Pro 20x"): (200, "/月", "用量为Plus的20倍；自2026-09-10起暂停售新订阅与升级，现有订阅可续费"),
            ("OpenAI", "ChatGPT Business Standard"): (25, "/席位/月", "月付价，年付$20/席位/月，至少2席位"),
            ("OpenAI", "ChatGPT Business Premium"): (125, "/席位/月", "月付价，年付$100/席位/月，5倍Standard用量；本次固定月费待复核(保留9月2日旧值)"),
            ("Google", "Google AI Plus"): (9.99, "/月", "美元官网含2TB；其他地区可能为400GB"),
            ("Google", "Google AI Ultra 5x"): (None, "地区定价", "含20TB存储，Gemini用量为Pro的5倍"),
            ("Google", "Google AI Ultra 20x"): (None, "地区定价", "含30TB存储，Gemini用量为Pro的20倍"),
            ("xAI", "SuperGrok Plus"): (100, "/月", "显著提高用量并支持1080p视频"),
            ("千问", "Token Plan 标准座席"): (150, "/座席/月", "限时价，原价¥198，25,000 Credits/座席/月"),
            ("千问", "Token Plan 高级座席"): (550, "/座席/月", "限时价，原价¥698，100,000 Credits/座席/月"),
            ("千问", "Token Plan 尊享座席"): (1398, "/座席/月", "250,000 Credits/座席/月"),
            ("千问", "Token Plan 共享用量包"): (5000, "/个/月", "625,000 Credits/个，供团队共享"),
            ("智谱AI", "GLM Coding Pro"): (72, "/月", "年付折合$50.4/月；本次固定月费待复核(保留9月2日旧值)"),
            ("智谱AI", "GLM Coding Max"): (160, "/月", "年付折合$112/月；本次固定月费待复核(保留9月2日旧值)"),
            ("Kimi", "Andante"): (49, "/月", "日常使用；连续包年更优惠"),
            ("Kimi", "Allegro"): (699, "/月", "全能尊享；连续包年更优惠"),
            ("Kimi", "Vivace（国际旧档）"): (199, "/月", "保留2026-09-02官方公开价；当前官方页面未直接展示，待复核"),
        }
        for key, expected in expected_plan_values.items():
            self.assertIn(key, plans_by_key)
            plan = plans_by_key[key]
            self.assertEqual((plan["price"], plan["billing"], plan["note"]), expected, key)

        provider_counts = {}
        for model in ai_data["models"]:
            provider_counts[model["provider"]] = provider_counts.get(model["provider"], 0) + 1
        self.assertEqual(len(ai_data["models"]), 40)
        self.assertEqual(provider_counts, {
            "OpenAI": 4, "Anthropic": 4, "Google": 5, "xAI": 7, "DeepSeek": 3,
            "千问": 4, "智谱AI": 6, "Kimi": 3, "Meta": 4,
        })
        models_by_name = {model["model"]: model for model in ai_data["models"]}
        self.assertEqual(
            (models_by_name["Claude Fable 5.1"]["cached_input_price"], models_by_name["Claude Fable 5.1"]["output_price"]),
            (0.25, 50.0),
        )
        self.assertEqual(
            (models_by_name["Qwen3.8 Flash"]["input_price"], models_by_name["Qwen3.8 Flash"]["cached_input_price"], models_by_name["Qwen3.8 Flash"]["output_price"]),
            (0.8, None, 2.7),
        )
        self.assertEqual(models_by_name["Qwen3.8 Max"]["cached_input_price"], 1.5)
        self.assertEqual(
            (
                models_by_name["GLM-5.3-Flash"]["input_price"],
                models_by_name["GLM-5.3-Flash"]["cached_input_price"],
                models_by_name["GLM-5.3-Flash"]["output_price"],
                models_by_name["GLM-5.3-Flash"]["status"],
            ),
            (0.15, 0.03, 0.5, "价格稳定"),
        )
        self.assertIn("class=\"ai-estimate-breakdown\"", response.text)
        self.assertIn('id="aiEstimatedInputCost"', response.text)
        self.assertIn('id="aiEstimatedOutputCost"', response.text)
        self.assertIn("display: flex; flex: 1; align-items: center; justify-content: space-between", style)

    def test_split_static_assets_are_served(self):
        with TestClient(app) as client:
            for path in (
                "/static/css/cards.css", "/static/css/wallet_cards.css", "/static/css/phones.css",
                "/static/js/cards.js", "/static/js/wallet_cards.js", "/static/js/phones.js",
            ):
                self.assertEqual(client.get(path).status_code, 200, path)

    def test_overseas_add_forms_start_collapsed(self):
        with TestClient(app) as client:
            expected = {
                "/cards": ('id="cardAddForm" class="sidebar-form collapsible-add-form is-collapsed"', 'id="toggleCardAddForm"'),
                "/wallet-cards": ('id="walletCardAddForm" class="wallet-card-form is-collapsed"', 'id="toggleWalletCardForm"'),
                "/phones": ('id="phoneAddForm" class="sidebar-form collapsible-add-form is-collapsed"', 'id="togglePhoneAddForm"'),
            }
            for path, markers in expected.items():
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-expanded="false"', response.text)
                for marker in markers:
                    self.assertIn(marker, response.text)

            wallet_page = client.get("/wallet-cards").text
            self.assertIn('<h1 class="page-title">境外卡</h1>', wallet_page)
            self.assertNotIn('<h1 class="page-title">我的境外卡</h1>', wallet_page)
            self.assertNotIn("本机私密保存", wallet_page)
            self.assertNotIn("记录卡片所属软件、卡号、CVC与账单资料", wallet_page)
            self.assertNotIn("卡号、CVC和地址会保存在本机", wallet_page)

            self.assertIn("添加境外工具", client.get("/cards").text)
            self.assertIn("添加境外卡", wallet_page)
            self.assertIn("添加境外号码", client.get("/phones").text)
            self.assertNotIn('class="wallet-form-full"><span>备注</span>', wallet_page)
            self.assertIn('id="addWalletCardAddress" rows="1"', wallet_page)
            self.assertIn('name="note" rows="1"', wallet_page)

    def test_wallet_cards_page_and_private_card_detail(self):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            cards_file = Path(temp_dir) / "wallet_cards.json"
            tools_file = Path(temp_dir) / "cards.json"
            tools_file.write_text(
                json.dumps(
                    [{
                        "id": 103,
                        "name": "测试工具",
                        "country": "示例地区",
                        "account_provider": "USD Card: Example (Example Bank)",
                    }],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with (
                patch("app.routers.wallet_cards.WALLET_CARDS_FILE", cards_file),
                patch("app.utils.WALLET_CARDS_FILE", cards_file),
                patch("app.utils.CARDS_FILE", tools_file),
                TestClient(app) as client,
            ):
                create_response = client.post(
                    "/wallet-cards/add",
                    data={
                        "name": "测试消费卡",
                        "software": "Wise",
                        "source_tool_id": "103",
                        "scheme": "Visa",
                        "card_variant": "Visa Platinum",
                        "cover_style": "decard-pink",
                        "card_number": "4111 1111 1111 1234",
                        "expiry": "08/29",
                        "cvc": "321",
                        "holder_name": "TEST USER",
                        "billing_address": "1 Test Road, London",
                        "note": "订阅专用",
                    },
                    follow_redirects=False,
                )
                self.assertEqual(create_response.status_code, 303)

                page = client.get("/wallet-cards")
                self.assertEqual(page.status_code, 200)
                self.assertIn('href="/wallet-cards" class="active">境外卡片</a>', page.text)
                self.assertIn('id="walletCardGrid"', page.text)
                self.assertIn("•••• •••• •••• 1234", page.text)
                self.assertIn("wallet-card-cover-decard-pink", page.text)
                self.assertNotIn("4111 1111 1111 1234", page.text)
                self.assertNotIn("321", page.text)
                self.assertNotIn("1 Test Road, London", page.text)

                detail = client.get("/api/wallet-cards/1")
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.headers.get("cache-control"), "no-store")
                self.assertEqual(detail.json()["card"]["card_number"], "4111 1111 1111 1234")
                self.assertEqual(detail.json()["card"]["cvc"], "321")
                self.assertEqual(detail.json()["card"]["billing_address"], "1 Test Road, London")
                self.assertEqual(detail.json()["card"]["card_variant"], "Visa Platinum")
                self.assertEqual(detail.json()["card"]["country"], "示例地区")
                self.assertIn("Example Bank", detail.json()["card"]["account_provider"])

        script = (project_root / "app/static/js/wallet_cards.js").read_text(encoding="utf-8")
        style = (project_root / "app/static/css/wallet_cards.css").read_text(encoding="utf-8")
        self.assertIn("const ITEMS_PER_PAGE = 9", script)
        self.assertIn("grid-template-columns: repeat(3", style)
        self.assertIn(".wallet-form-grid", style)
        self.assertIn("grid-template-columns: repeat(2", style)
        for cover_style in ("decard-pink", "etherfi-prism", "plasma-dark", "plasma-light"):
            self.assertIn(f"wallet-card-cover-{cover_style}", style)
        self.assertIn("bindSourceTool", script)
        self.assertIn("#ff4a3d", style)

    def test_pjax_navigation_ignores_stale_responses(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (project_root / "app/static/js/app.js").read_text(encoding="utf-8")
        self.assertIn("new AbortController()", script)
        self.assertIn("navigationId !== activeNavigationId", script)
        self.assertIn('error.name === "AbortError"', script)

        script = (project_root / "app/static/js/wallet_cards.js").read_text(encoding="utf-8")
        style = (project_root / "app/static/css/wallet_cards.css").read_text(encoding="utf-8")
        self.assertIn("const ITEMS_PER_PAGE = 9", script)
        self.assertIn("grid-template-columns: repeat(3", style)
        self.assertIn(".wallet-form-grid", style)
        self.assertIn("grid-template-columns: repeat(2", style)
        for cover_style in ("decard-pink", "etherfi-prism", "plasma-dark", "plasma-light"):
            self.assertIn(f"wallet-card-cover-{cover_style}", style)
        self.assertIn("bindSourceTool", script)
        self.assertIn("#ff4a3d", style)

    def test_pjax_navigation_ignores_stale_responses(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (project_root / "app/static/js/app.js").read_text(encoding="utf-8")
        self.assertIn("new AbortController()", script)
        self.assertIn("navigationId !== activeNavigationId", script)
        self.assertIn('error.name === "AbortError"', script)
        with TestClient(app) as client:
            self.assertIn('/static/js/app.js?v=1.0.11', client.get("/").text)

    def test_all_pagination_variants_use_the_shared_ui(self):
        project_root = Path(__file__).resolve().parents[1]
        style = (project_root / "app/static/css/style.css").read_text(encoding="utf-8")
        self.assertIn(".pagination-container", style)
        self.assertIn(".pagination-controls", style)
        self.assertIn("background: #ff5a52", style)

        pagination_sources = (
            project_root / "app/templates/base.html",
            project_root / "app/templates/daily_briefing.html",
            project_root / "app/templates/stock_detail.html",
            project_root / "app/static/js/cards.js",
            project_root / "app/static/js/phones.js",
        )
        for source_path in pagination_sources:
            source = source_path.read_text(encoding="utf-8")
            self.assertIn("page-btn", source, source_path.name)
            self.assertNotIn("stylePaginationBtn", source, source_path.name)
            self.assertNotIn("border-radius: 999px", source, source_path.name)

        with TestClient(app) as client:
            cards_page = client.get("/cards")
            phones_page = client.get("/phones")
            self.assertIn('/static/js/cards.js?v=1.0.7', cards_page.text)
            self.assertIn('/static/js/phones.js?v=1.0.3', phones_page.text)
            self.assertIn('« 上一页', client.get("/static/js/cards.js?v=1.0.7").text)
            self.assertIn('下一页 »', client.get("/static/js/phones.js?v=1.0.2").text)

    def test_daily_briefing_selects_latest_date_by_default(self):
        with TestClient(app) as client:
            response = client.get("/daily-briefing")
            self.assertEqual(response.status_code, 200)
            self.assertIn('<a href="/daily-briefing" class="active">每日简报</a>', response.text)
            self.assertIn('<h1 class="page-title">每日简报</h1>', response.text)
            self.assertNotIn("请选择一个日期查看每日简报", response.text)
            with SessionLocal() as session:
                latest_date = session.query(func.max(DailyReport.date)).scalar()
                logical_count = (
                    session.query(func.count(func.distinct(DailyReport.title)))
                    .filter(DailyReport.date == latest_date)
                    .scalar()
                )
            if logical_count:
                self.assertIn(f"简报文件 ({logical_count})", response.text)

    def test_stock_card_lookup_prefers_exact_header_over_news_mentions(self):
        msft_report = """
<div class="row stock">
  <div>🏷️ 微软 MSFT ｜ 板块：科技服务 / 软件产品</div>
  <div>新闻：MSFT, DELL, UBER, ASTS, AVGO In Focus</div>
</div>
"""
        avgo_report = """
<div class="row stock">
  <div>🏷️ 博通 AVGO ｜ 板块：电子科技 / 半导体芯片</div>
</div>
"""

        card_html = _find_stock_card_html([msft_report, avgo_report], "AVGO")

        self.assertIsNotNone(card_html)
        self.assertIn("博通 AVGO ｜", card_html)
        self.assertNotIn("微软 MSFT ｜", card_html)

    def test_holdings_has_currency_selector_and_rejects_unknown_currency(self):
        with TestClient(app) as client:
            page = client.get("/holdings")
            self.assertIn('id="portfolio-base-currency"', page.text)
            self.assertIn("<span>总成本</span>", page.text)
            self.assertIn("<th>累计收益率</th>", page.text)
            self.assertIn("<th>当日涨跌幅</th>", page.text)
            self.assertIn('data-value="pnl_percent"', page.text)
            self.assertIn('data-value="daily_change_percent"', page.text)
            self.assertIn("data.summary.total_pnl_percent_text", page.text)
            self.assertNotIn('id="summary-base-currency"', page.text)
            self.assertNotIn("总成本（", page.text)
            for currency in ("CNY", "USD", "HKD"):
                self.assertIn(f'value="{currency}"', page.text)
            response = client.get("/api/holdings/quotes?base_currency=EUR")
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
