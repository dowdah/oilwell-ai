import multiprocessing
import os
from pathlib import Path

import pytest

from edge_agent.sequence import SequenceAllocator
from edge_agent.single_writer import SingleWriterLock, SingleWriterLockError


def _hold_lock(state_dir: str, device_id: str, ready, release) -> None:
    lock = SingleWriterLock(Path(state_dir), device_id)
    lock.acquire()
    ready.set()
    release.wait(10)
    lock.release()


def _crash_with_lock(state_dir: str, device_id: str, ready) -> None:
    lock = SingleWriterLock(Path(state_dir), device_id)
    lock.acquire()
    ready.set()
    os._exit(0)


def test_second_writer_fails_without_touching_sequence_state(tmp_path):
    state = tmp_path / "sequence.json"
    first = SequenceAllocator(state, lease_size=5)
    before = state.read_bytes()
    ready, release = multiprocessing.Event(), multiprocessing.Event()
    process = multiprocessing.Process(target=_hold_lock, args=(str(tmp_path), "edge-pi-01", ready, release))
    process.start()
    assert ready.wait(5)

    second = SingleWriterLock(tmp_path, "edge-pi-01")
    with pytest.raises(SingleWriterLockError, match="single writer lock already held"):
        second.acquire()
    assert state.read_bytes() == before
    assert first.reserved_until > 0

    release.set()
    process.join(5)
    assert process.exitcode == 0


def test_lock_releases_after_normal_exit_and_keeps_sequence(tmp_path):
    state = tmp_path / "sequence.json"
    lock = SingleWriterLock(tmp_path, "edge-pi-01")
    lock.acquire()
    first = SequenceAllocator(state, lease_size=5)
    high_water = first.reserved_until
    lock.release()

    next_lock = SingleWriterLock(tmp_path, "edge-pi-01")
    next_lock.acquire()
    next_allocator = SequenceAllocator(state, lease_size=5)
    assert next_allocator.reserved_until > high_water
    next_lock.release()


def test_lock_releases_after_process_crash_and_sequence_moves_forward(tmp_path):
    state = tmp_path / "sequence.json"
    previous = SequenceAllocator(state, lease_size=5).reserved_until
    ready = multiprocessing.Event()
    process = multiprocessing.Process(target=_crash_with_lock, args=(str(tmp_path), "edge-pi-01", ready))
    process.start()
    assert ready.wait(5)
    process.join(5)
    assert process.exitcode == 0

    lock = SingleWriterLock(tmp_path, "edge-pi-01")
    lock.acquire()
    resumed = SequenceAllocator(state, lease_size=5)
    assert resumed.reserved_until > previous
    lock.release()


def test_different_devices_use_independent_locks(tmp_path):
    first = SingleWriterLock(tmp_path, "edge-pi-01")
    second = SingleWriterLock(tmp_path, "edge-pi-02")
    first.acquire()
    second.acquire()
    assert first.path != second.path
    first.release()
    second.release()


def test_device_filename_is_safe(tmp_path):
    lock = SingleWriterLock(tmp_path, "edge/pi 01")
    assert lock.path.name == "writer-edge_pi_01.lock"
