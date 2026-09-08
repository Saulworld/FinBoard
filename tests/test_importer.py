import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.importer import run_import


class ImporterPathTests(unittest.TestCase):
    def test_run_import_uses_only_current_source_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_dir = root / "00_核心数据"
            report_dir = root / "01_简报正文"
            backup_dir = root / "06_备份归档"
            core_dir.mkdir()
            report_dir.mkdir()
            backup_dir.mkdir()
            history_path = core_dir / "股票评估历史.csv"
            history_path.write_text("date,ticker\n", encoding="utf-8")
            (backup_dir / "每日简报-2026.8.10-总览.html").write_text("旧版", encoding="utf-8")

            with (
                patch("app.importer.get_briefing_dir", return_value=root),
                patch("app.importer.import_daily_briefings", return_value=0) as import_briefings,
                patch("app.importer.import_daily_reports", return_value=0) as import_reports,
            ):
                run_import(Mock())

            import_briefings.assert_called_once_with(unittest.mock.ANY, history_path)
            import_reports.assert_called_once_with(unittest.mock.ANY, report_dir)

