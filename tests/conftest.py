from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def tmp_runtime(tmp_path, monkeypatch):
    """Aísla db/, logs/, state/, output/ en un tmp_path por test.

    El motor escribe rutas relativas a la cwd. Para tests deterministas
    cambiamos cwd al tmp y dejamos que cree sus propias carpetas.
    """
    for sub in ('db', 'logs', 'state', 'output', 'configs', 'flows'):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.fixture()
def project_root() -> Path:
    return ROOT
