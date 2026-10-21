from contextlib import closing
from pathlib import Path
import json, os, sqlite3, subprocess, sys, tempfile, unittest, zipfile
from scripts.local_backup import (
    ROOT,
    create_snapshot,
    verify_snapshot,
    restore_snapshot,
    offline_lock,
)
from app.json_store import load_json, save_json_atomic
from unittest.mock import patch


class LocalProtectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            dir=ROOT / ".runtime", prefix="restore-test-"
        )
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "app").mkdir()
        (self.root / ".runtime").mkdir()
        (self.root / "LOCAL_EDITION.json").write_text(
            json.dumps(
                {
                    "edition": "local-glass",
                    "source_root": str(ROOT.parent / "protected-test-archive"),
                }
            ),
            encoding="utf-8",
        )
        self.original = b'[{"id":1,"name":"unchanged","extra":"keep"}]\n'
        (self.root / "data/cards.json").write_bytes(self.original)
        (self.root / "app/sample.py").write_text("version=1\n", encoding="utf-8")
        with closing(sqlite3.connect(self.root / "data/portfolio.db")) as db:
            db.execute("create table items(id integer, value text)")
            db.execute("insert into items values(1,'preserved')")
            db.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_restore_preserves_data_and_creates_safety_snapshot(self):
        snapshot = create_snapshot("test", "full", self.root)
        verify_snapshot(snapshot["path"])
        (self.root / "data/cards.json").write_text("[]", encoding="utf-8")
        (self.root / "app/sample.py").write_text("version=2", encoding="utf-8")
        (self.root / "app/new.py").write_text("new", encoding="utf-8")
        with closing(sqlite3.connect(self.root / "data/portfolio.db")) as db:
            db.execute("delete from items")
            db.commit()
        with offline_lock(self.root):
            result = restore_snapshot(snapshot["name"], self.root)
        self.assertEqual((self.root / "data/cards.json").read_bytes(), self.original)
        self.assertEqual((self.root / "app/sample.py").read_text(), "version=1\n")
        self.assertFalse((self.root / "app/new.py").exists())
        self.assertTrue(
            (self.root / "backups/local" / result["safety_backup"]).exists()
        )
        with closing(sqlite3.connect(self.root / "data/portfolio.db")) as db:
            self.assertEqual(
                db.execute("select value from items").fetchone()[0], "preserved"
            )

    def test_corrupt_snapshot_refused_before_data_changes(self):
        snapshot = create_snapshot("test", "data", self.root)
        path = Path(snapshot["path"])
        with zipfile.ZipFile(path) as z:
            members = {n: z.read(n) for n in z.namelist()}
        members["data/cards.json"] = b"[]"
        with zipfile.ZipFile(path, "w") as z:
            for name, value in members.items():
                z.writestr(name, value)
        with self.assertRaises(RuntimeError):
            restore_snapshot(snapshot["name"], self.root)
        self.assertEqual((self.root / "data/cards.json").read_bytes(), self.original)

    def test_pre_migration_marker_is_rejected_before_restore(self):
        marker_path = self.root / "LOCAL_EDITION.json"
        current_marker = marker_path.read_bytes()
        snapshot = create_snapshot("pre-migration", "full", self.root)
        path = Path(snapshot["path"])
        import hashlib

        with zipfile.ZipFile(path) as z:
            members = {name: z.read(name) for name in z.namelist()}
        marker = json.loads(current_marker)
        marker["source_root"] = str(self.root)
        payload = json.dumps(marker).encode("utf-8")
        members["LOCAL_EDITION.json"] = payload
        manifest = json.loads(members["SNAPSHOT.json"])
        manifest["files"]["LOCAL_EDITION.json"] = {
            "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)
        }
        members["SNAPSHOT.json"] = json.dumps(manifest).encode("utf-8")
        with zipfile.ZipFile(path, "w") as z:
            for name, value in members.items():
                z.writestr(name, value)
        verify_snapshot(path)
        with self.assertRaisesRegex(RuntimeError, "迁移前目录"):
            restore_snapshot(snapshot["name"], self.root)
        self.assertEqual(marker_path.read_bytes(), current_marker)
        self.assertEqual((self.root / "data/cards.json").read_bytes(), self.original)

    def test_running_copy_lock_prevents_second_process(self):
        with offline_lock(self.root):
            with self.assertRaises(RuntimeError):
                with offline_lock(self.root):
                    pass

    def test_data_snapshot_does_not_replace_code(self):
        snapshot = create_snapshot("test", "data", self.root)
        (self.root / "app/sample.py").write_text("version=2", encoding="utf-8")
        with offline_lock(self.root):
            restore_snapshot(snapshot["name"], self.root)
        self.assertEqual((self.root / "app/sample.py").read_text(), "version=2")

    def test_cached_json_is_not_shared_and_invalid_json_cannot_be_silently_reset(self):
        path = self.root / "data/cards.json"
        value = load_json(path, [])
        value[0]["extra"] = "changed only in memory"
        self.assertEqual(load_json(path, [])[0]["extra"], "keep")
        save_json_atomic(path, [{"id": 2}])
        self.assertEqual(load_json(path, [])[0]["id"], 2)
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            load_json(path, [])
        self.assertEqual(path.read_text(), "{broken")

    def test_external_database_is_rejected(self):
        env = dict(os.environ)
        env["DATABASE_URL"] = f"sqlite:///{(ROOT.parent / 'other-project' / 'portfolio.db').as_posix()}"
        proc = subprocess.run(
            [sys.executable, "-c", "import app.config"],
            cwd=ROOT,
            env=env,
            capture_output=True,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_backup_failure_blocks_mutation(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.config import PROJECT_ROOT
        from app.utils import PHONES_FILE

        before = PHONES_FILE.read_bytes() if PHONES_FILE.exists() else None
        with (
            patch("app.config.DATA_DIR", PROJECT_ROOT / "data"),
            patch(
                "scripts.local_backup.create_snapshot",
                side_effect=RuntimeError("simulated disk failure"),
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/phones/add",
                    data={"name": "must-not-save", "phone": "0", "country": "德国"},
                )
                self.assertEqual(response.status_code, 503)
        after = PHONES_FILE.read_bytes() if PHONES_FILE.exists() else None
        self.assertEqual(after, before)
