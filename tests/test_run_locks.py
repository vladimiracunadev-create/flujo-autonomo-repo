from engine.database import (
    acquire_run_lock,
    force_release_lock,
    init_db,
    list_run_locks,
    release_run_lock,
)


def test_lock_acquire_and_release(tmp_runtime):
    init_db()
    assert acquire_run_lock("flow_a", "run-1") is True
    assert acquire_run_lock("flow_a", "run-2") is False
    locks = list_run_locks()
    assert len(locks) == 1 and locks[0]["folder"] == "flow_a"
    release_run_lock("flow_a", "run-1")
    assert acquire_run_lock("flow_a", "run-3") is True
    force_release_lock("flow_a")
    assert list_run_locks() == []


def test_lock_independent_per_folder(tmp_runtime):
    init_db()
    assert acquire_run_lock("flow_a", "r1") is True
    assert acquire_run_lock("flow_b", "r2") is True
    assert {row["folder"] for row in list_run_locks()} == {"flow_a", "flow_b"}
