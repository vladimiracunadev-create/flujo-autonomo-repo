import uuid

from engine.database import (
    acquire_run_lock,
    force_release_lock,
    init_db,
    list_run_locks,
    release_run_lock,
)


def test_lock_acquire_and_release(tmp_runtime):
    init_db()
    folder = f"flow_{uuid.uuid4().hex[:8]}"
    try:
        assert acquire_run_lock(folder, "run-1") is True
        assert acquire_run_lock(folder, "run-2") is False
        assert any(row["folder"] == folder for row in list_run_locks())
        release_run_lock(folder, "run-1")
        assert acquire_run_lock(folder, "run-3") is True
    finally:
        force_release_lock(folder)


def test_lock_independent_per_folder(tmp_runtime):
    init_db()
    a = f"flow_{uuid.uuid4().hex[:8]}"
    b = f"flow_{uuid.uuid4().hex[:8]}"
    try:
        assert acquire_run_lock(a, "r1") is True
        assert acquire_run_lock(b, "r2") is True
        folders = {row["folder"] for row in list_run_locks()}
        assert {a, b} <= folders
    finally:
        force_release_lock(a)
        force_release_lock(b)
