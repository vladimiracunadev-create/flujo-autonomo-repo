from __future__ import annotations

import json
from pathlib import Path

from engine.loader import FlowLoader


def _write_flow(tmp: Path, manifest: dict, context: dict | None = None) -> Path:
    flow_dir = tmp / "flows" / manifest["id"]
    flow_dir.mkdir(parents=True, exist_ok=True)
    (flow_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if context is not None:
        (flow_dir / "context.example.json").write_text(json.dumps(context), encoding="utf-8")
    return flow_dir


def test_load_manifest_minimal(tmp_path):
    flow_dir = _write_flow(tmp_path, {
        "id": "demo",
        "name": "Demo",
        "steps": [{"id": "s1", "action": "system.wait_seconds", "params": {"seconds": 0}}],
    })
    definition = FlowLoader.load_manifest(flow_dir)
    assert definition.id == "demo"
    assert definition.steps[0].action == "system.wait_seconds"
    assert definition.max_steps_per_run == 200


def test_load_context_uses_example(tmp_path):
    flow_dir = _write_flow(
        tmp_path,
        {"id": "demo", "name": "Demo", "steps": [{"id": "s1", "action": "x.y"}]},
        context={"path_override": "data/x"},
    )
    ctx = FlowLoader.load_context(flow_dir)
    assert ctx == {"path_override": "data/x"}


def test_load_context_explicit_path_wins(tmp_path):
    flow_dir = _write_flow(
        tmp_path,
        {"id": "demo", "name": "Demo", "steps": [{"id": "s1", "action": "x.y"}]},
        context={"a": 1},
    )
    explicit = tmp_path / "other.json"
    explicit.write_text(json.dumps({"a": 99}), encoding="utf-8")
    ctx = FlowLoader.load_context(flow_dir, explicit_context_path=explicit)
    assert ctx == {"a": 99}
