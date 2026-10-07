"""JSON persistence for the interview app.

This intentionally supports one local backend process only. Production would use
a database, durable job queue, object storage, and an audit trail.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


class JsonRepository:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._thread_lock = threading.RLock()

    def read(self, name: str, default: Any) -> Any:
        path = self._path(name)
        if not path.exists():
            self.write(name, default)
            return default
        with self._locked(path):
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)

    def write(self, name: str, value: Any) -> None:
        path = self._path(name)
        with self._locked(path):
            fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=self.data_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(value, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def _path(self, name: str) -> Path:
        if name not in {"documents", "jobs", "program_setup", "program_inventory"}:
            raise ValueError("Unknown JSON collection")
        return self.data_dir / f"{name}.json"

    def _locked(self, path: Path):
        return _FileLock(self._thread_lock, path.with_suffix(path.suffix + ".lock"))


class _FileLock:
    def __init__(self, thread_lock: threading.RLock, lock_path: Path):
        self.thread_lock = thread_lock
        self.lock_path = lock_path
        self.handle = None

    def __enter__(self):
        self.thread_lock.acquire()
        self.handle = self.lock_path.open("a+")
        try:
            import fcntl
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - Windows development fallback
            pass
        return self

    def __exit__(self, *_exc):
        try:
            try:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            except ImportError:  # pragma: no cover
                pass
            self.handle.close()
        finally:
            self.thread_lock.release()
