from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def flatten_context(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in data.items():
        compound = f"{prefix}.{key}" if prefix else key
        result[compound] = value
        if isinstance(value, dict):
            result.update(flatten_context(value, compound))
    return result


def _resolve_exact_placeholder(text: str, flat: Dict[str, Any]) -> Any:
    match = re.fullmatch(r"\{\s*([^{}]+?)\s*\}", text)
    if not match:
        return None
    key = match.group(1).strip()
    return flat.get(key)


def render_value(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        prepared = value.replace("{{", "{").replace("}}", "}")
        flat = flatten_context(context)
        flat["now"] = now
        exact = _resolve_exact_placeholder(prepared, flat)
        if exact is not None:
            return exact
        return prepared.format_map(SafeDict(flat))
    if isinstance(value, dict):
        return {k: render_value(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [render_value(v, context) for v in value]
    return value
