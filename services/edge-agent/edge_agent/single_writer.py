"""Durable per-device process ownership for an Edge state volume."""

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re


class SingleWriterLockError(RuntimeError):
    """Raised when another process holds the device writer lock."""


def _safe_device_filename(device_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", device_id).strip("._")
    if not safe:
        raise ValueError("device_id must contain a filesystem-safe character")
    return safe


class SingleWriterLock:
    """Keep a non-blocking advisory lock open for one Edge process lifetime."""

    def __init__(self, state_dir: Path, device_id: str):
        self.path = state_dir / f"writer-{_safe_device_filename(device_id)}.lock"
        self.device_id = device_id
        self._fd: int | None = None

    def acquire(self) -> None:
        if self._fd is not None:
            raise RuntimeError("single writer lock is already acquired by this process")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(fd)
            raise SingleWriterLockError("single writer lock already held") from exc
        except Exception:
            os.close(fd)
            raise

        self._fd = fd
        diagnostic = json.dumps(
            {
                "device_id": self.device_id,
                "pid": os.getpid(),
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        ).encode()
        os.ftruncate(fd, 0)
        os.write(fd, diagnostic)
        os.fsync(fd)

    def release(self) -> None:
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

