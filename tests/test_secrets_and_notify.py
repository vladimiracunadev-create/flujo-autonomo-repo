from __future__ import annotations

from pathlib import Path

import pytest

from actions.notify import send_notification
from engine import secrets as secrets_mod


def test_get_secret_env_priority(monkeypatch, tmp_path):
    monkeypatch.setenv("FA_T1", "from_env")
    monkeypatch.setattr(secrets_mod, "SECRETS_PATH", tmp_path / "secrets.json")
    (tmp_path / "secrets.json").write_text('{"FA_T1": "from_file"}', encoding="utf-8")
    assert secrets_mod.get_secret("FA_T1") == "from_env"


def test_get_secret_falls_back_to_file(monkeypatch, tmp_path):
    monkeypatch.delenv("FA_T2", raising=False)
    monkeypatch.setattr(secrets_mod, "SECRETS_PATH", tmp_path / "secrets.json")
    (tmp_path / "secrets.json").write_text('{"FA_T2": "from_file"}', encoding="utf-8")
    assert secrets_mod.get_secret("FA_T2") == "from_file"


def test_set_and_get_secret(monkeypatch, tmp_path):
    monkeypatch.setattr(secrets_mod, "SECRETS_PATH", tmp_path / "secrets.json")
    monkeypatch.delenv("FA_T3", raising=False)
    secrets_mod.set_secret("FA_T3", "abc")
    assert secrets_mod.get_secret("FA_T3") == "abc"


def test_notify_log_backend(capsys):
    out = send_notification("hola", backend="log")
    assert out["sent"] is True
    captured = capsys.readouterr()
    assert "hola" in captured.out


def test_notify_file_backend(tmp_path):
    target = tmp_path / "log.tsv"
    out = send_notification("evento", backend="file", target=str(target))
    assert out["sent"] is True
    content = target.read_text(encoding="utf-8")
    assert "evento" in content


def test_notify_unknown_backend_raises():
    with pytest.raises(ValueError):
        send_notification("x", backend="weird")


def test_notify_webhook_requires_target():
    with pytest.raises(ValueError):
        send_notification("x", backend="webhook")
