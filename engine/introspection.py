from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_existing_paths(data: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def walk(value: Any, trail: str = "root") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{trail}.{key}")
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{trail}[{index}]")
            return
        if isinstance(value, str):
            candidate = Path(value)
            if candidate.exists() and candidate.is_file() and str(candidate) not in seen:
                seen.add(str(candidate))
                found.append(
                    {
                        "path": str(candidate),
                        "name": candidate.name,
                        "size_bytes": candidate.stat().st_size,
                        "source": trail,
                    }
                )

    walk(data)
    return sorted(found, key=lambda item: item["path"])
