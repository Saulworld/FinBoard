from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Callable, Iterator, TypeVar


T = TypeVar("T")
_locks_guard = threading.Lock()
_locks: dict[Path, threading.RLock] = {}


def _lock_for(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _locks_guard:
        return _locks.setdefault(resolved, threading.RLock())


@contextmanager
def json_file_transaction(path: Path) -> Iterator[None]:
    """Serialize a complete read-modify-write transaction within this process."""
    with _lock_for(path):
        yield


def load_json(path: Path, default: T) -> T:
    with json_file_transaction(path):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError, TypeError):
            return default


def save_json_atomic(path: Path, value: Any) -> None:
    """Write JSON to a sibling temp file, fsync it, then atomically replace the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with json_file_transaction(path):
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                json.dump(value, handle, ensure_ascii=False, indent=4)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            temp_name = None
        finally:
            if temp_name:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass


def update_json(path: Path, default: T, updater: Callable[[T], T | None]) -> T:
    """Atomically perform an in-process read-modify-write operation."""
    with json_file_transaction(path):
        current = load_json(path, default)
        updated = updater(current)
        result = current if updated is None else updated
        save_json_atomic(path, result)
        return result
