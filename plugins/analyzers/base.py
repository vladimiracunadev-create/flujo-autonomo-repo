from __future__ import annotations

from pathlib import Path
from typing import Protocol, Dict, Any


class AnalyzerProtocol(Protocol):
    def analyze(self, image_path: Path) -> Dict[str, Any]:
        ...
