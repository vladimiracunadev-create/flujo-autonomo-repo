from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class AnalyzerProtocol(Protocol):
    def analyze(self, image_path: Path) -> dict[str, Any]:
        ...
