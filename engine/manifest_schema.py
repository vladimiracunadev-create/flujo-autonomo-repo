"""Validación de manifests con JSON Schema (con fallback ligero).

Si la dependencia opcional ``jsonschema`` está disponible se aplica la spec
completa de ``schemas/manifest.schema.json``. Si no, se cae a un check
estructural mínimo que cubre los campos críticos.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from engine.paths import root_dir

SCHEMA_PATH = root_dir() / 'schemas' / 'manifest.schema.json'


def _load_schema() -> Dict[str, Any]:
    with SCHEMA_PATH.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def validate_manifest_data(data: Dict[str, Any]) -> List[str]:
    """Devuelve lista de errores. Vacía = válido."""
    errors: List[str] = []
    try:
        import jsonschema  # type: ignore
        from jsonschema import Draft202012Validator  # type: ignore
    except ImportError:
        return _fallback_validate(data)

    schema = _load_schema()
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        location = '/'.join(str(p) for p in err.absolute_path) or '<root>'
        errors.append(f'{location}: {err.message}')
    return errors


def _fallback_validate(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ['raíz: el manifest debe ser un objeto JSON']
    for required in ('id', 'name', 'steps'):
        if required not in data:
            errors.append(f'<root>: falta campo requerido {required!r}')
    steps = data.get('steps')
    if not isinstance(steps, list) or not steps:
        errors.append('steps: debe ser una lista no vacía')
        return errors
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f'steps[{index}]: debe ser objeto')
            continue
        if not step.get('id'):
            errors.append(f'steps[{index}]: falta id')
        if not step.get('action'):
            errors.append(f'steps[{index}]: falta action')
    return errors


def validate_manifest_file(path: Path) -> List[str]:
    with path.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    return validate_manifest_data(data)
