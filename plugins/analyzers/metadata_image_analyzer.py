from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image


class MetadataImageAnalyzer:
    def analyze(self, image_path: Path) -> dict[str, Any]:
        raw = image_path.read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()
        with Image.open(image_path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "sha256": sha256,
                "summary": "Analizador local de metadatos de imagen.",
            }
