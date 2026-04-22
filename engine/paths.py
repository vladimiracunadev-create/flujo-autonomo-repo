from __future__ import annotations

from pathlib import Path


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent
