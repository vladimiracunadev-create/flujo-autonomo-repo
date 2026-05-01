"""Smoke tests por acción que no requieren GUI ni red."""
from __future__ import annotations

import pytest

from actions import filesystem, rules, system, ui


def test_ensure_directory_creates(tmp_path):
    target = tmp_path / "nuevo"
    out = filesystem.ensure_directory(str(target))
    assert out["exists"] and target.is_dir()


def test_list_directory_counts_files(tmp_path):
    (tmp_path / "a.txt").write_text("hola")
    (tmp_path / "b.md").write_text("xy")
    out = filesystem.list_directory(str(tmp_path))
    assert out["total_files"] == 2
    extensions = {item["extension"] for item in out["files"]}
    assert {".txt", ".md"} <= extensions


def test_classify_inventory_aggregates():
    files = [
        {"name": "a.txt", "extension": ".txt", "size_bytes": 100},
        {"name": "b.txt", "extension": ".txt", "size_bytes": 50},
        {"name": "big.bin", "extension": ".bin", "size_bytes": 9999},
    ]
    out = filesystem.classify_file_inventory(files)
    assert out["total_files"] == 3
    assert out["by_extension"][".txt"] == 2
    assert out["largest_file"]["name"] == "big.bin"


def test_write_json_roundtrip(tmp_path):
    target = tmp_path / "out.json"
    filesystem.write_json(str(target), {"a": 1})
    assert target.exists()
    assert '"a": 1' in target.read_text(encoding="utf-8")


def test_rules_evaluate_first_match_wins():
    decision = rules.evaluate_rules(
        input_data={"snapshot": {"memory_percent": 92}},
        rules=[
            {"id": "mem_alta", "path": "snapshot.memory_percent", "operator": "gt", "value": 85, "status": "alerta"},
        ],
        default_status="ok",
    )
    assert decision["status"] == "alerta"
    assert decision["matched_rule"]["id"] == "mem_alta"


def test_rules_evaluate_default_when_no_match():
    decision = rules.evaluate_rules(
        input_data={"snapshot": {"memory_percent": 10}},
        rules=[
            {"id": "mem_alta", "path": "snapshot.memory_percent", "operator": "gt", "value": 85, "status": "alerta"},
        ],
        default_status="ok",
    )
    assert decision["status"] == "ok"


def test_system_wait_zero():
    assert system.wait_seconds(0)["waited_seconds"] == 0


def test_ui_launch_process_dry_run():
    out = ui.launch_process("echo hola", dry_run=True)
    assert out["dry_run"] is True
    assert out["launched"] is False


def test_ui_launch_process_empty_raises():
    with pytest.raises(ValueError):
        ui.launch_process("", dry_run=True)


def test_ui_hotkey_dry_run():
    out = ui.hotkey(["ctrl", "s"], dry_run=True)
    assert out["dry_run"] is True


def test_ui_click_dry_run():
    out = ui.click(10, 20, dry_run=True)
    assert out["dry_run"] is True


def test_ui_click_bbox_centers():
    out = ui.click_bbox({"left": 0, "top": 0, "width": 100, "height": 50}, dry_run=True)
    assert out["x"] == 50 and out["y"] == 25
