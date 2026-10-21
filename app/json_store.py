from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import threading
from copy import deepcopy
from typing import Any, Callable, Iterator, TypeVar


T = TypeVar("T")
_locks_guard = threading.Lock()
_locks: dict[Path, threading.RLock] = {}
_read_cache: dict[Path, tuple[tuple[int, int], Any]] = {}


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
            return deepcopy(default)
        try:
            resolved = path.resolve()
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            cached = _read_cache.get(resolved)
            if cached and cached[0] == signature:
                return deepcopy(cached[1])
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            # Copy on read: callers may add display-only fields without polluting the cache.
            if len(_read_cache) > 64:
                _read_cache.clear()
            _read_cache[resolved] = (signature, value)
            return deepcopy(value)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError(
                f"无法读取{path.name}，已停止操作以保护原有数据。"
            ) from exc


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
            _read_cache.pop(path.resolve(), None)
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
