"""Cada manifest del repo debe pasar la validación contra el schema."""
from __future__ import annotations

from pathlib import Path

import pytest

from engine.manifest_schema import validate_manifest_data, validate_manifest_file

REPO_ROOT = Path(__file__).resolve().parent.parent


def _flow_manifests():
    return sorted((REPO_ROOT / "flows").glob("*/manifest.json"))


@pytest.mark.parametrize("manifest_path", _flow_manifests(), ids=lambda p: p.parent.name)
def test_repo_manifests_validate(manifest_path):
    errors = validate_manifest_file(manifest_path)
    assert errors == [], f"Manifest inválido: {errors}"


def test_validate_rejects_missing_required():
    errors = validate_manifest_data({"name": "x"})
    assert errors  # falta id, falta steps


def test_validate_rejects_bad_id_pattern():
    errors = validate_manifest_data({
        "id": "Invalid-Id",
        "name": "x",
        "steps": [{"id": "a", "action": "x.y"}],
    })
    assert any("id" in e for e in errors)


def test_validate_rejects_unknown_step_field():
    errors = validate_manifest_data({
        "id": "abc",
        "name": "x",
        "steps": [{"id": "a", "action": "x.y", "frob": True}],
    })
    assert errors


def test_validate_accepts_minimal_valid():
    errors = validate_manifest_data({
        "id": "minimal_demo",
        "name": "Demo",
        "steps": [{"id": "s1", "action": "system.wait_seconds", "params": {"seconds": 0}}],
    })
    assert errors == []
