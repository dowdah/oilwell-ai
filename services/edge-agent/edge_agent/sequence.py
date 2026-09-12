"""Reserve durable sequence ranges so restarts cannot reuse accepted telemetry IDs."""
import json
import os
from pathlib import Path
import time


class SequenceAllocator:
    def __init__(self, path: Path | None = None, lease_size: int = 10_000):
        self.path, self.lease_size = path, lease_size
        previous = 0
        if path is not None and path.exists():
            payload = json.loads(path.read_text())
            if payload.get('schema') != 1 or not isinstance(payload.get('reserved_until'), int):
                raise ValueError('invalid sequence state; restore the durable state instead of resetting it')
            previous = payload['reserved_until']
        self.value = max(time.time_ns() // 1000, previous)
        self._reserve()

    def _reserve(self):
        self.reserved_until = self.value + self.lease_size
        if self.reserved_until > 9_007_199_254_740_991:
            raise ValueError('sequence exhausted JavaScript safe integer range')
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            with temporary.open('w') as output:
                json.dump({'schema': 1, 'reserved_until': self.reserved_until}, output)
                output.flush(); os.fsync(output.fileno())
            temporary.replace(self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)

    def next(self):
        if self.value >= self.reserved_until: self._reserve()
        self.value += 1
        return self.value
