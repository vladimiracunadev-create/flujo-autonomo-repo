from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.orchestrator import FlowExecutionError, Orchestrator
from engine.sandbox import SandboxPolicy, SandboxViolation


def _write_manifest(flow_dir: Path, manifest: dict) -> None:
    flow_dir.mkdir(parents=True, exist_ok=True)
    (flow_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_policy_permissive_by_default():
    p = SandboxPolicy()
    assert p.is_permissive() is True
    assert p.check_required_secrets() == []


def test_policy_blocks_unallowed_action():
    p = SandboxPolicy(allowed_actions=["a.b"])
    p.assert_action_allowed("a.b")
    with pytest.raises(SandboxViolation):
        p.assert_action_allowed("x.y")


def test_policy_required_secrets_missing(monkeypatch):
    monkeypatch.delenv("FA_TEST_SECRET", raising=False)
    p = SandboxPolicy(required_secrets=["FA_TEST_SECRET"])
    assert p.check_required_secrets() == ["FA_TEST_SECRET"]
    with pytest.raises(SandboxViolation):
        p.assert_secrets_present()


def test_policy_required_secrets_present(monkeypatch):
    monkeypatch.setenv("FA_TEST_SECRET", "1")
    p = SandboxPolicy(required_secrets=["FA_TEST_SECRET"])
    p.assert_secrets_present()


def test_policy_path_allowlist_blocks_outside(tmp_path):
    base = tmp_path / "ok"
    base.mkdir()
    p = SandboxPolicy(allowed_paths=[str(base)])
    p.assert_paths_allowed({"path": str(base / "file.txt")})
    with pytest.raises(SandboxViolation):
        p.assert_paths_allowed({"path": str(tmp_path / "fuera.txt")})


def test_policy_path_allowlist_ignores_unrendered_placeholders(tmp_path):
    p = SandboxPolicy(allowed_paths=[str(tmp_path)])
    p.assert_paths_allowed({"path": "/anywhere/{var}.txt"})  # no debe romper


@pytest.mark.integration
def test_orchestrator_blocks_unallowed_action(tmp_runtime):
    flow_dir = tmp_runtime / "flows" / "blocked"
    _write_manifest(flow_dir, {
        "id": "blocked",
        "name": "Blocked",
        "allowed_actions": ["filesystem.write_json"],
        "steps": [{"id": "s1", "action": "system.wait_seconds", "params": {"seconds": 0}}],
    })
    with pytest.raises(FlowExecutionError) as exc:
        Orchestrator(flow_dir=flow_dir).run()
    assert "allowed_actions" in str(exc.value) or "bloqueada" in str(exc.value)


@pytest.mark.integration
def test_orchestrator_blocks_missing_secret(tmp_runtime, monkeypatch):
    monkeypatch.delenv("FA_REQUIRED_X", raising=False)
    flow_dir = tmp_runtime / "flows" / "secret"
    _write_manifest(flow_dir, {
        "id": "secret_flow",
        "name": "Secret",
        "required_secrets": ["FA_REQUIRED_X"],
        "steps": [{"id": "s1", "action": "system.wait_seconds", "params": {"seconds": 0}}],
    })
    with pytest.raises(FlowExecutionError):
        Orchestrator(flow_dir=flow_dir).run()
