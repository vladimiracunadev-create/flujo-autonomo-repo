from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import requests


def fetch_url(url: str, output_path: str | None = None, timeout: float = 15.0) -> Dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    result = {
        "url": url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "content_length": len(response.text),
    }
    if output_path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(response.text, encoding="utf-8")
        result["output_path"] = str(target)
    return result
