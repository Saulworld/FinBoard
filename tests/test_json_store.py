import tempfile
import threading
import unittest
from pathlib import Path

from app.json_store import load_json, save_json_atomic, update_json


class JsonStoreTests(unittest.TestCase):
    def test_concurrent_updates_are_not_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "counter.json"
            save_json_atomic(path, {"count": 0})

            def increment():
                for _ in range(25):
                    update_json(path, {"count": 0}, lambda value: {"count": value["count"] + 1})

            threads = [threading.Thread(target=increment) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(load_json(path, {})["count"], 200)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
