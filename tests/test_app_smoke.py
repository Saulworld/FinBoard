import json
import re
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
            for path in (
                "/",
                "/holdings",
                "/cards",
                "/overseas-documents",
                "/wallet-cards",
                "/phones",
                "/ai-monitor",
            ):
                response = client.get(path)
                self.assertEqual(
                    response.status_code, 200, f"{path}: {response.text[:300]}"
                )

    def test_overseas_documents_private_register(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            documents_file = Path(temp_dir) / "overseas_documents.json"
            options_file = Path(temp_dir) / "overseas_document_options.json"
            documents_file.write_text("[]", encoding="utf-8")
            example_addresses = [
                {"country": "马来西亚", "address": "2 Example Road, Malaysia（马来西亚）"},
                {"country": "菲律宾", "address": "3 Example Road, Philippines（菲律宾）"},
            ]
            with (patch("app.routers.overseas_documents.DOCUMENTS_FILE", documents_file),
                  patch("app.routers.overseas_documents.OPTIONS_FILE", options_file),
                  patch("app.routers.overseas_documents.ADDRESS_OPTIONS", example_addresses),
                  TestClient(app) as client):
                payload = {
                    "country": "英国", "document_type": "税号(TIN)",
                    "number": "AB-12345678", "holder": "TEST USER",
                    "issued_on": "2026-01-01", "expires_on": "",
                    "issuer": "Test Authority", "address": "1 Test Road, London", "note": "private note",
                }
                created = client.post("/overseas-documents/add", data=payload, follow_redirects=False)
                self.assertEqual(created.status_code, 303)
                passport = client.post("/overseas-documents/add", data={**payload, "country": "中国", "document_type": "护照", "number": "P12345678", "address": ""}, follow_redirects=False)
                self.assertEqual(passport.status_code, 303)
                identity = client.post("/overseas-documents/add", data={**payload, "country": "马来西亚", "document_type": "身份证", "number": "ID12345678", "address": ""}, follow_redirects=False)
                self.assertEqual(identity.status_code, 303)
                philippines = client.post("/overseas-documents/add", data={**payload, "country": "菲律宾", "document_type": "税号(TIN)", "number": "TIN12345678", "address": ""}, follow_redirects=False)
                self.assertEqual(philippines.status_code, 303)
                page = client.get("/overseas-documents")
                self.assertEqual(page.status_code, 200)
                self.assertIn("英国", page.text)
                self.assertIn("税号1", page.text)
                self.assertIn("护照1", page.text)
                self.assertIn("身份证1", page.text)
                self.assertIn("•••• 5678", page.text)
                self.assertIn('class="document-cover document-cover-standard"', page.text)
                self.assertIn('class="document-cover document-cover-china"', page.text)
                self.assertIn('class="document-cover document-cover-malaysia"', page.text)
                self.assertIn('class="document-cover document-cover-philippines"', page.text)
                self.assertIn('id="addDocumentType"', page.text)
                self.assertIn('id="editDocumentType"', page.text)
                self.assertIn('id="documentTypeModal"', page.text)
                self.assertEqual(page.text.count('name="address"'), 2)
                self.assertIn('name="note" rows="1"', page.text)
                self.assertIn("证件号 *", page.text)
                self.assertNotIn("证件号或税号", page.text)
                self.assertNotIn('id="documentTypeOptions"', page.text)
                self.assertNotIn('id="documentCountryFilter"', page.text)
                self.assertNotIn('id="documentTypeFilter"', page.text)
                self.assertNotIn("AB-12345678", page.text)
                self.assertNotIn("private note", page.text)
                self.assertNotIn("1 Test Road, London", page.text)
                detail = client.get("/api/overseas-documents/1")
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.headers.get("cache-control"), "no-store")
                self.assertEqual(detail.json()["document"]["number"], "AB-12345678")
                self.assertEqual(detail.json()["document"]["address"], "1 Test Road, London")
                self.assertEqual(client.get("/api/overseas-documents/2").json()["document"]["address"], "")
                self.assertEqual(client.get("/api/overseas-documents/3").json()["document"]["address"], example_addresses[0]["address"])
                self.assertEqual(client.get("/api/overseas-documents/4").json()["document"]["address"], example_addresses[1]["address"])
                self.assertIn("税号(TIN)", client.get("/api/overseas-document-options").json()["document_types"])
                self.assertEqual(client.post("/api/overseas-document-options", json={"document_types": []}).status_code, 400)
                saved_options = client.post("/api/overseas-document-options", json={"document_types": ["身份证", "护照"]})
                self.assertEqual(saved_options.status_code, 200)
                self.assertEqual(saved_options.json()["document_types"], ["身份证", "护照"])
                before_records = documents_file.read_bytes()
                saved_countries = client.post("/api/overseas-document-options", json={"countries": ["英国", "中国"]})
                self.assertEqual(saved_countries.status_code, 200)
                self.assertEqual(saved_countries.json()["countries"], ["英国", "中国"])
                self.assertEqual(saved_countries.json()["document_types"], ["身份证", "护照"])
                self.assertEqual(client.post("/api/overseas-document-options", json={"countries": []}).status_code, 400)
                self.assertEqual(client.post("/api/overseas-document-options", json={"countries": [42]}).status_code, 400)
                self.assertEqual(documents_file.read_bytes(), before_records)
                self.assertIn("documents-manage-countries", client.get("/overseas-documents").text)
                self.assertEqual(client.get("/api/overseas-documents/1").json()["document"]["document_type"], "税号(TIN)")

                bad = client.post("/overseas-documents/1/update", data={**payload, "expires_on": "2025-01-01"})
                self.assertEqual(bad.status_code, 400)
                self.assertEqual(client.get("/api/overseas-documents/1").json()["document"]["number"], "AB-12345678")
                updated = client.post("/overseas-documents/1/update", data={**payload, "number": "UK-99991234", "address": "2 Test Road, London"})
                self.assertEqual(updated.status_code, 200)
                self.assertEqual(client.get("/api/overseas-documents/1").json()["document"]["number"], "UK-99991234")
                self.assertEqual(client.get("/api/overseas-documents/1").json()["document"]["address"], "2 Test Road, London")
                omitted_address = {key: value for key, value in payload.items() if key != "address"}
                self.assertEqual(client.post("/overseas-documents/1/update", data=omitted_address).status_code, 200)
                self.assertEqual(client.get("/api/overseas-documents/1").json()["document"]["address"], "2 Test Road, London")
                deleted = client.post("/overseas-documents/1/delete")
                self.assertEqual(deleted.status_code, 200)
                self.assertEqual(client.get("/api/overseas-documents/1").status_code, 404)

    def test_ai_monitor_has_models_and_plan_switcher(self):
        project_root = Path(__file__).resolve().parents[1]
        ai_data = json.loads(
            (project_root / "data/ai_monitor.json").read_text(encoding="utf-8")
        )
        with TestClient(app) as client:
            response = client.get("/ai-monitor")
            self.assertEqual(response.status_code, 200)
            for marker in (
                'data-ai-tab="api"',
                'data-ai-tab="plans"',
                "data-plan-select",
                "data-model-select",
                'id="aiUpdatesPagination"',
                "const updatesPerPage = 5",
                "ChatGPT Pro 100",
                "ChatGPT Pro 200",
                "ChatGPT Pro 500",
                "ChatGPT Business Premium",
                "Claude Max 20x",
                "Google AI Ultra 20x",
                "SuperGrok Plus",
                "Token Plan Pro",
                "Token Plan 共享用量包",
                "GLM Coding Max",
                "Andante",
                "Vivace",
                "GPT-5.6 Sol",
                "GPT-5.6 Luna",
                "GPT-6 Sol",
                "GPT-6.1 Sol",
                "GPT-6 Luna",
                "Claude Opus 5.5",
                "Grok 4.7",
                "Claude Fable 5.1",
                "Claude Haiku 4.5",
                "Claude Haiku 5.5",
                "Gemini 3.5 Flash-Lite",
                "Gemini 3.6 Flash",
                "Gemini 3.1 Pro Preview",
                "Token Plan Essential",
                "Google AI Pro（英国）",
                "Grok Build 0.1",
                "Grok 4.20 Multi-Agent",
                "DeepSeek V4 Pro",
                "Qwen3.7 Plus",
                "Qwen3.8 Flash",
                "Qwen3 Coder Flash",
                "GLM-5.2",
                "GLM-5 Turbo",
                "GLM-4.5 Air",
                "Kimi K2.7 Code",
                "Kimi K2.6",
                "Muse Spark 1.3",
                "Muse Spark 1.2",
                "Muse Spark 1.1",
                "Muse Glimmer",
                "Meta Model API",
                "function updateModelRow(row)",
            ):
                self.assertIn(marker, response.text)
            self.assertEqual(response.text.count(" data-plan-card>"), 9)
            self.assertEqual(response.text.count("<tr data-model-row"), 9)
            self.assertEqual(
                response.text.count(
                    '<select class="ai-model-select" data-model-select'
                ),
                9,
            )
            self.assertEqual(response.text.count("data-price="), len(ai_data["plans"]))
            self.assertIn("按量计费", response.text)
            self.assertNotIn("ai-count-badge", response.text)
            self.assertNotIn("种套餐", response.text)
            self.assertNotIn("40种", response.text)
            self.assertNotIn("选择厂商套餐即可查看对应价格", response.text)
            first_openai_model = re.search(
                r'<tr data-model-row[^>]*data-provider="OpenAI".*?<option[^>]*>([^<]+)</option>',
                response.text,
                re.S,
            )
            first_openai_plan = re.search(
                r'<article class="ai-plan-card openai" data-plan-card>.*?<option[^>]*>([^<]+)</option>',
                response.text,
                re.S,
            )
            self.assertIsNotNone(first_openai_model)
            self.assertIsNotNone(first_openai_plan)
            self.assertEqual(first_openai_model.group(1), "GPT-6.1 Sol")
            self.assertEqual(first_openai_plan.group(1), "ChatGPT Plus")

        style = (project_root / "app/static/css/ai_monitor.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("min-height: 300px", style)
        self.assertIn("min-height: 60px", style)
        self.assertIn(
            ".ai-calculator-card { display: flex; flex-direction: column; }", style
        )
        self.assertIn(".ai-model-select", style)
        self.assertIn("/static/css/ai_monitor.css?v=", response.text)

        self.assertGreaterEqual(len(ai_data["plans"]), 73)
        plans_by_key = {
            (plan["provider"], plan["plan"]): plan for plan in ai_data["plans"]
        }
        expected_plan_values = {
            ("OpenAI", "ChatGPT Pro 100"): (100, "/月", "现行$100月付档；不含Ultrafast"),
            ("OpenAI", "ChatGPT Pro 200"): (
                200,
                "/月",
                "标准月付$200；9月22日至29日符合资格的旧订阅保留原额度至2026-10-29",
            ),
            ("OpenAI", "ChatGPT Pro 500"): (500, "/月", "最高包含用量；含Astra与Sol Ultrafast"),
            ("OpenAI", "ChatGPT Business Standard"): (
                25,
                "/席位/月",
                "月付价，年付$20/席位/月，至少2席位",
            ),
            ("OpenAI", "ChatGPT Business Premium"): (
                125,
                "/席位/月",
                "月付$125/席位，年付折算$100/席位/月；5倍Standard用量、无5小时限额",
            ),
            ("Google", "Google AI Plus"): (
                9.99,
                "/月",
                "美国标准月付$9.99，含2TB",
            ),
            ("Google", "Google AI Plus（英国）"): (
                7.99,
                "/月",
                "英国Google One公开月付价",
            ),
            ("Google", "Google AI Pro（英国）"): (
                18.99,
                "/月",
                "英国Google One公开月付价",
            ),
            ("Google", "Google AI Ultra 5x"): (
                None,
                "地区定价",
                "官方比较表确认5倍Pro用量、20TB",
            ),
            ("Google", "Google AI Ultra 20x"): (
                None,
                "地区定价",
                "官方比较表确认20倍Pro用量、30TB",
            ),
            ("xAI", "SuperGrok Plus（旧档）"): (100, "/月", "显著提高用量并支持1080p视频"),
            ("千问", "Token Plan 标准座席"): (
                198,
                "/座席/月",
                "标准月付¥198；官网限时¥150，25,000 Credits/座席/月",
            ),
            ("千问", "Token Plan Essential"): (
                120,
                "/月",
                "标准月付¥120；官网现行限时¥79，25,500 Credits/月",
            ),
            ("千问", "Token Plan 高级座席"): (
                698,
                "/座席/月",
                "标准月付¥698；官网限时¥550，100,000 Credits/座席/月",
            ),
            ("千问", "Token Plan 尊享座席"): (
                1398,
                "/座席/月",
                "250,000 Credits/座席/月",
            ),
            ("千问", "Token Plan 共享用量包"): (
                5000,
                "/个/月",
                "625,000 Credits/个，供团队共享",
            ),
            ("智谱AI", "GLM Coding Pro"): (
                80,
                "/月",
                "官方标价$80/月；另列优惠$56/月",
            ),
            ("智谱AI", "GLM Coding Max"): (
                168,
                "/月",
                "官方标价$168/月；另列优惠$117.6/月",
            ),
            ("Kimi", "Andante（旧档）"): (49, "/月", "日常使用；连续包年更优惠"),
            ("Kimi", "Allegro（旧档）"): (699, "/月", "全能尊享；连续包年更优惠"),
            ("Google", "Google AI Plus（香港）"): (79, "/月", "香港官方月付价、2TB"),
            ("智谱AI", "GLM Coding Lite(国内)"): (118, "/月", "官方标价¥118/月"),
            ("Anthropic", "Team Scientists Premium"): (15, "/席位/月", "科研组审核后$15月付"),
            ("Kimi", "Vivace（国际旧档）"): (
                199,
                "/月",
                "保留2026-09-02官方美元旧价",
            ),
        }
        for key, expected in expected_plan_values.items():
            self.assertIn(key, plans_by_key)
            plan = plans_by_key[key]
            self.assertEqual((plan["price"], plan["billing"]), expected[:2], key)
            self.assertTrue(plan["note"].startswith(expected[2]), key)

        provider_counts = {}
        for model in ai_data["models"]:
            provider_counts[model["provider"]] = (
                provider_counts.get(model["provider"], 0) + 1
            )
        self.assertGreaterEqual(len(ai_data["models"]), 48)
        for provider, minimum in {
            "OpenAI": 6, "Anthropic": 7, "Google": 4, "xAI": 8,
            "DeepSeek": 2, "千问": 4, "智谱AI": 7, "Kimi": 3, "Meta": 4,
        }.items():
            self.assertGreaterEqual(provider_counts.get(provider, 0), minimum, provider)
        models_by_name = {model["model"]: model for model in ai_data["models"]}
        self.assertEqual(
            tuple(models_by_name["GPT-6.1 Sol"][key] for key in ("input_price", "cached_input_price", "output_price", "context")),
            (2.0, 0.1, 10.0, "1.05M"),
        )
        self.assertEqual(
            tuple(models_by_name["GLM-5.3（国际）"][key] for key in ("currency", "input_price", "cached_input_price", "output_price")),
            ("USD", 1.4, 0.26, 4.4),
        )
        self.assertEqual(
            (
                models_by_name["Claude Sonnet 5.5"]["input_price"],
                models_by_name["Claude Sonnet 5.5"]["cached_input_price"],
                models_by_name["Claude Sonnet 5.5"]["output_price"],
                models_by_name["Claude Sonnet 5.5"]["context"],
            ),
            (2.0, 0.1, 10.0, "1M"),
        )
        self.assertEqual(
            (
                models_by_name["Gemini 3.6 Flash"]["input_price"],
                models_by_name["Gemini 3.6 Flash"]["cached_input_price"],
                models_by_name["Gemini 3.6 Flash"]["output_price"],
            ),
            (0.75, 0.075, 3.75),
        )
        self.assertEqual(
            (
                models_by_name["Claude Fable 5.1"]["cached_input_price"],
                models_by_name["Claude Fable 5.1"]["output_price"],
            ),
            (0.25, 50.0),
        )
        self.assertEqual(
            (
                models_by_name["Qwen3.8 Flash"]["input_price"],
                models_by_name["Qwen3.8 Flash"]["cached_input_price"],
                models_by_name["Qwen3.8 Flash"]["output_price"],
            ),
            (0.8, 0.1, 2.7),
        )
        self.assertEqual(models_by_name["Qwen3.8 Max"]["cached_input_price"], 1.5)
        self.assertEqual(
            tuple(models_by_name["Claude Haiku 5.5"][key] for key in ("input_price", "cached_input_price", "output_price", "context")),
            (0.1, 0.01, 0.5, "1M"),
        )
        self.assertIn(">100K", models_by_name["Claude Haiku 5.5"]["pricing_note"])
        self.assertNotIn("Gemini 3.7 Flash", models_by_name)
        self.assertNotIn("Gemini 3.5 Flash", models_by_name)
        self.assertIn("旧3.7 Flash请求自动转发", models_by_name["Gemini 3.8 Flash"]["pricing_note"])
        self.assertIn("旧3.5 Flash请求自动转发", models_by_name["Gemini 3.6 Flash"]["pricing_note"])
        self.assertIn("Ultrafast为6倍", models_by_name["GPT-6.1 Sol"]["pricing_note"])
        self.assertIn("每月$100官方API额度", plans_by_key[("Anthropic", "Claude Max 5x")]["note"])
        self.assertEqual(plans_by_key[("Google", "Google AI Plus（香港）")]["currency_symbol"], "HK$")
        self.assertNotIn("DeepSeek V4 Flash Vision Exp", models_by_name)
        self.assertEqual(
            (
                models_by_name["DeepSeek V4.1 Flash"]["input_price"],
                models_by_name["DeepSeek V4.1 Flash"]["cached_input_price"],
                models_by_name["DeepSeek V4.1 Flash"]["output_price"],
            ),
            (0.3, 0.006, 1.2),
        )
        self.assertEqual(
            plans_by_key[("Google", "Google AI Pro（台湾）")]["currency_symbol"], "NT$"
        )
        self.assertIsNone(plans_by_key[("Kimi", "会员加油包")]["price"])

        self.assertEqual(
            (
                models_by_name["GLM-5.3-Flash"]["input_price"],
                models_by_name["GLM-5.3-Flash"]["cached_input_price"],
                models_by_name["GLM-5.3-Flash"]["output_price"],
                models_by_name["GLM-5.3-Flash"]["status"],
            ),
            (0.15, 0.03, 0.5, "价格稳定"),
        )
        self.assertIn('class="ai-estimate-breakdown"', response.text)
        self.assertIn('id="aiEstimatedInputCost"', response.text)
        self.assertIn('id="aiEstimatedOutputCost"', response.text)
        self.assertIn(
            "display: flex; flex: 1; align-items: center; justify-content: space-between",
            style,
        )

    def test_split_static_assets_are_served(self):
        with TestClient(app) as client:
            for path in (
                "/static/css/cards.css",
                "/static/css/wallet_cards.css",
                "/static/css/phones.css",
                "/static/js/cards.js",
                "/static/js/wallet_cards.js",
                "/static/js/phones.js",
            ):
                self.assertEqual(client.get(path).status_code, 200, path)

    def test_overseas_add_forms_start_collapsed(self):
        with TestClient(app) as client:
            expected = {
                "/cards": (
                    'id="cardAddForm" class="sidebar-form collapsible-add-form is-collapsed"',
                    'id="toggleCardAddForm"',
                ),
                "/wallet-cards": (
                    'id="walletCardAddForm" class="wallet-card-form is-collapsed"',
                    'id="toggleWalletCardForm"',
                ),
                "/phones": (
                    'id="phoneAddForm" class="sidebar-form collapsible-add-form is-collapsed"',
                    'id="togglePhoneAddForm"',
                ),
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

    def test_cards_notice_panel_adds_and_displays_plain_reminders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            notices_file = Path(temp_dir) / "card_notices.json"
            notices_file.write_text("[]", encoding="utf-8")
            with (
                patch("app.routers.cards.CARD_NOTICES_FILE", notices_file),
                patch("app.utils.CARD_NOTICES_FILE", notices_file),
                TestClient(app) as client,
            ):
                empty_page = client.get("/cards")
                self.assertEqual(empty_page.status_code, 200)
                self.assertIn('id="cardNoticesTitle">注意事项</h2>', empty_page.text)
                self.assertIn('id="cardNoticeForm"', empty_page.text)
                self.assertNotIn(
                    'name="expiry_date"',
                    empty_page.text.split('id="cardNoticeForm"', 1)[1].split(
                        "</form>", 1
                    )[0],
                )

                response = client.post(
                    "/cards/notices/add",
                    data={"content": "Wirex系列产品都无法使用CN护照注册"},
                    follow_redirects=False,
                )
                self.assertEqual(response.status_code, 303)

                page = client.get("/cards")
                self.assertIn("Wirex系列产品都无法使用CN护照注册", page.text)
                stored = json.loads(notices_file.read_text(encoding="utf-8"))
                self.assertEqual(
                    stored[0]["content"], "Wirex系列产品都无法使用CN护照注册"
                )
                self.assertNotIn("expiry_date", stored[0])

                update_response = client.post(
                    "/cards/notices/1/update",
                    data={"content": "Wirex系列产品暂时无法使用CN护照注册"},
                )
                self.assertEqual(update_response.status_code, 200)
                self.assertEqual(
                    update_response.json()["content"],
                    "Wirex系列产品暂时无法使用CN护照注册",
                )
                updated_page = client.get("/cards")
                self.assertIn("Wirex系列产品暂时无法使用CN护照注册", updated_page.text)
                updated = json.loads(notices_file.read_text(encoding="utf-8"))
                self.assertEqual(
                    updated[0]["content"], "Wirex系列产品暂时无法使用CN护照注册"
                )
                self.assertIn("updated_at", updated[0])

        project_root = Path(__file__).resolve().parents[1]
        notice_style = (project_root / "app/static/css/cards.css").read_text(
            encoding="utf-8"
        )
        notice_script = (project_root / "app/static/js/cards.js").read_text(
            encoding="utf-8"
        )
        self.assertIn(".edit-card-notice-btn {\n    display: none;", notice_style)
        self.assertIn(
            ".card-notices-panel.is-managing .edit-card-notice-btn", notice_style
        )
        self.assertIn('classList.toggle("is-managing", expanded)', notice_script)
        self.assertIn(".card-notice-form {", notice_style)
        self.assertIn("transition: none;", notice_style)

    def test_wallet_cards_page_and_private_card_detail(self):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            cards_file = Path(temp_dir) / "wallet_cards.json"
            tools_file = Path(temp_dir) / "cards.json"
            tools_file.write_text(
                json.dumps(
                    [
                        {
                            "id": 103,
                            "name": "测试工具",
                            "country": "示例地区",
                            "account_provider": "USD Card: Example (Example Bank)",
                        }
                    ],
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
                self.assertRegex(
                    page.text,
                    r'href="/wallet-cards" class="active">.*?<span>境外卡片</span></a>',
                )
                self.assertIn('id="walletCardGrid"', page.text)
                self.assertIn("•••• •••• •••• 1234", page.text)
                self.assertIn("wallet-card-cover-decard-pink", page.text)
                self.assertNotIn("4111 1111 1111 1234", page.text)
                self.assertNotIn("321", page.text)
                self.assertNotIn("1 Test Road, London", page.text)

                detail = client.get("/api/wallet-cards/1")
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.headers.get("cache-control"), "no-store")
                self.assertEqual(
                    detail.json()["card"]["card_number"], "4111 1111 1111 1234"
                )
                self.assertEqual(detail.json()["card"]["cvc"], "321")
                self.assertEqual(
                    detail.json()["card"]["billing_address"], "1 Test Road, London"
                )
                self.assertEqual(detail.json()["card"]["card_variant"], "Visa Platinum")
                self.assertEqual(detail.json()["card"]["country"], "示例地区")
                self.assertIn("Example Bank", detail.json()["card"]["account_provider"])

        script = (project_root / "app/static/js/wallet_cards.js").read_text(
            encoding="utf-8"
        )
        style = (project_root / "app/static/css/wallet_cards.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("const ITEMS_PER_PAGE = 9", script)
        self.assertIn("grid-template-columns: repeat(3", style)
        self.assertIn(".wallet-form-grid", style)
        self.assertIn("grid-template-columns: repeat(2", style)
        for cover_style in (
            "decard-pink",
            "etherfi-prism",
            "plasma-dark",
            "plasma-light",
        ):
            self.assertIn(f"wallet-card-cover-{cover_style}", style)
        self.assertIn("bindSourceTool", script)
        self.assertIn("#ff4a3d", style)

    def test_pjax_navigation_ignores_stale_responses(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (project_root / "app/static/js/app.js").read_text(encoding="utf-8")
        self.assertIn("new AbortController()", script)
        self.assertIn("navigationId !== activeNavigationId", script)
        self.assertIn('error.name === "AbortError"', script)

        script = (project_root / "app/static/js/wallet_cards.js").read_text(
            encoding="utf-8"
        )
        style = (project_root / "app/static/css/wallet_cards.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("const ITEMS_PER_PAGE = 9", script)
        self.assertIn("grid-template-columns: repeat(3", style)
        self.assertIn(".wallet-form-grid", style)
        self.assertIn("grid-template-columns: repeat(2", style)
        for cover_style in (
            "decard-pink",
            "etherfi-prism",
            "plasma-dark",
            "plasma-light",
        ):
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
            self.assertIn("/static/js/app.js?v=2.1.0", client.get("/").text)

    def test_all_pagination_variants_use_the_shared_ui(self):
        project_root = Path(__file__).resolve().parents[1]
        style = (project_root / "app/static/css/style.css").read_text(encoding="utf-8")
        self.assertIn(".pagination-container", style)
        self.assertIn(".pagination-controls", style)
        self.assertIn("background: #ff5a52", style)

        pagination_sources = (
            project_root / "app/static/js/shell.js",
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
            self.assertIn("/static/js/cards.js?v=20260930-3", cards_page.text)
            self.assertIn("/static/js/phones.js?v=20260930-3", phones_page.text)
            self.assertIn("« 上一页", client.get("/static/js/cards.js?v=20260930-3").text)
            self.assertIn("下一页 »", client.get("/static/js/phones.js?v=20260930-3").text)

    def test_daily_briefing_selects_latest_date_by_default(self):
        with TestClient(app) as client:
            response = client.get("/daily-briefing")
            self.assertEqual(response.status_code, 200)
            self.assertRegex(
                response.text,
                r'<a href="/daily-briefing" class="active">.*?<span>每日简报</span></a>',
            )
            self.assertIn('<h1 class="page-title">每日简报</h1>', response.text)
            with SessionLocal() as session:
                latest_date = session.query(func.max(DailyReport.date)).scalar()
                logical_count = (
                    session.query(func.count(func.distinct(DailyReport.title)))
                    .filter(DailyReport.date == latest_date)
                    .scalar()
                )
            if logical_count:
                self.assertNotIn("请选择一个日期查看每日简报", response.text)
                self.assertIn(f"简报文件 ({logical_count})", response.text)
            else:
                self.assertIn("请选择一个日期查看每日简报", response.text)

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
            if 'id="holdingsTable"' in page.text:
                self.assertIn("<th>累计收益率</th>", page.text)
                self.assertIn("<th>当日涨跌幅</th>", page.text)
                self.assertIn('data-value="pnl_percent"', page.text)
                self.assertIn('data-value="daily_change_percent"', page.text)
            else:
                self.assertIn("还没有持仓记录。", page.text)
            self.assertIn("data.summary.total_pnl_percent_text", page.text)
            self.assertNotIn('id="summary-base-currency"', page.text)
            self.assertNotIn("总成本（", page.text)
            for currency in ("CNY", "USD", "HKD"):
                self.assertIn(f'value="{currency}"', page.text)
            response = client.get("/api/holdings/quotes?base_currency=EUR")
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
