"""Run regression tests against a disposable local data copy, never the delivered data."""

from pathlib import Path
import os, shutil, sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".runtime"
runtime.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="test-data-", dir=runtime) as temporary:
    for p in (ROOT / "data").iterdir():
        if p.is_file() and not p.name.endswith(("-wal", "-shm")):
            shutil.copy2(p, Path(temporary) / p.name)
    os.environ["FINBOARD_LOCAL_DATA_DIR"] = temporary
    os.environ.pop("DATABASE_URL", None)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    from app.db import engine

    engine.dispose()
sys.exit(not result.wasSuccessful())
