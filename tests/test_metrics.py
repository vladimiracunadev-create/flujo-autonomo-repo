from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.metrics import by_flow, overview, prometheus_text
from engine.orchestrator import Orchestrator


def _write_manifest(flow_dir: Path, manifest: dict) -> None:
    flow_dir.mkdir(parents=True, exist_ok=True)
    (flow_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.mark.integration
def test_overview_after_runs(tmp_runtime):
    flow_dir = tmp_runtime / "flows" / "metrics_demo"
    _write_manifest(flow_dir, {
        "id": "metrics_demo",
        "name": "Metrics",
        "steps": [{"id": "s1", "action": "system.wait_seconds", "params": {"seconds": 0}}],
    })
    Orchestrator(flow_dir=flow_dir).run()
    Orchestrator(flow_dir=flow_dir).run()

    o = overview()
    assert o["totals_by_status"].get("completed", 0) >= 2
    assert o["window"]["completed"] >= 2

    flows = by_flow()
    assert any(item["flow_id"] == "metrics_demo" for item in flows)


@pytest.mark.integration
def test_prometheus_text_format(tmp_runtime):
    flow_dir = tmp_runtime / "flows" / "prom_demo"
    _write_manifest(flow_dir, {
        "id": "prom_demo",
        "name": "Prom",
        "steps": [{"id": "s1", "action": "system.wait_seconds", "params": {"seconds": 0}}],
    })
    Orchestrator(flow_dir=flow_dir).run()

    text = prometheus_text()
    assert "flujo_runs_total" in text
    assert "# HELP" in text
    assert "# TYPE" in text
