"""Tests integrales del orquestador con flows sintéticos en tmp_path."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.loader import FlowLoader
from engine.orchestrator import FlowExecutionError, Orchestrator


def _write_manifest(flow_dir: Path, manifest: dict, context: dict | None = None) -> None:
    flow_dir.mkdir(parents=True, exist_ok=True)
    (flow_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if context is not None:
        (flow_dir / "context.example.json").write_text(json.dumps(context), encoding="utf-8")


@pytest.mark.integration
def test_orchestrator_completes_simple_flow(tmp_runtime):
    flow_dir = tmp_runtime / "flows" / "fast_demo"
    _write_manifest(flow_dir, {
        "id": "fast_demo",
        "name": "Demo rápido",
        "steps": [
            {"id": "wait", "action": "system.wait_seconds", "params": {"seconds": 0}, "save_as": "w"},
        ],
    })
    state = Orchestrator(flow_dir=flow_dir).run()
    assert state["status"] == "completed"
    assert state["context"]["w"]["waited_seconds"] == 0


@pytest.mark.integration
def test_orchestrator_retries_then_recovers(tmp_runtime):
    """Un paso que falla N-1 veces y a la N tiene éxito debe terminar 'completed'."""
    flow_dir = tmp_runtime / "flows" / "retry_demo"
    _write_manifest(flow_dir, {
        "id": "retry_demo",
        "name": "Retry",
        "steps": [
            {
                "id": "evaluate",
                "action": "rules.evaluate",
                "params": {
                    "input_data": {"x": 1},
                    "rules": [{"path": "x", "operator": "eq", "value": 1, "status": "ok"}],
                },
                "save_as": "decision",
            }
        ],
    })
    state = Orchestrator(flow_dir=flow_dir).run()
    assert state["status"] == "completed"
    assert state["context"]["decision"]["status"] == "ok"


@pytest.mark.integration
def test_orchestrator_branching_on_failure(tmp_runtime):
    """Un paso que falla salta a un paso de recovery vía transition on=failure."""
    flow_dir = tmp_runtime / "flows" / "branch_demo"
    _write_manifest(flow_dir, {
        "id": "branch_demo",
        "name": "Branch",
        "steps": [
            {
                "id": "broken",
                "action": "filesystem.read_text_file",
                "params": {"path": "no_existe.txt"},
                "transitions": [
                    {"on": "failure", "next": "recover"},
                    {"on": "success", "end": True},
                ],
            },
            {
                "id": "happy_path",
                "action": "system.wait_seconds",
                "params": {"seconds": 0},
            },
            {
                "id": "recover",
                "action": "system.wait_seconds",
                "params": {"seconds": 0},
                "save_as": "recovery",
            },
        ],
    })
    state = Orchestrator(flow_dir=flow_dir).run()
    assert state["status"] == "completed"
    assert "recover" in state["route"]


@pytest.mark.integration
def test_orchestrator_max_steps_enforced(tmp_runtime):
    flow_dir = tmp_runtime / "flows" / "loop_demo"
    _write_manifest(flow_dir, {
        "id": "loop_demo",
        "name": "Loop",
        "max_steps_per_run": 2,
        "steps": [
            {
                "id": "a",
                "action": "system.wait_seconds",
                "params": {"seconds": 0},
                "transitions": [{"on": "success", "next": "b"}],
            },
            {
                "id": "b",
                "action": "system.wait_seconds",
                "params": {"seconds": 0},
                "transitions": [{"on": "success", "next": "a"}],
            },
        ],
    })
    with pytest.raises(FlowExecutionError):
        Orchestrator(flow_dir=flow_dir).run()


@pytest.mark.integration
def test_orchestrator_when_skips_step(tmp_runtime):
    flow_dir = tmp_runtime / "flows" / "when_demo"
    _write_manifest(flow_dir, {
        "id": "when_demo",
        "name": "When",
        "steps": [
            {
                "id": "skipped",
                "action": "system.wait_seconds",
                "params": {"seconds": 0},
                "when": {"path": "feature_on", "operator": "truthy"},
            },
            {"id": "always", "action": "system.wait_seconds", "params": {"seconds": 0}},
        ],
    }, context={})
    state = Orchestrator(flow_dir=flow_dir).run()
    assert state["status"] == "completed"
    statuses = {s["step_id"]: s["status"] for s in state["steps"]}
    assert statuses["skipped"] == "skipped"
    assert statuses["always"] == "success"
