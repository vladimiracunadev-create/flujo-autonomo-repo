"""Validador de manifests, acciones y transiciones.

Aplica:
- JSON Schema (``schemas/manifest.schema.json``) si ``jsonschema`` está disponible.
- Checks estructurales adicionales: acciones registradas, transitions resueltas,
  start_step válido, allowed_actions consistente.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.action_registry import ACTION_REGISTRY  # noqa: E402
from engine.manifest_schema import validate_manifest_data  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def _validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    manifest = _load_json(path)
    flow_label = path.parent.name

    schema_errors = validate_manifest_data(manifest)
    errors.extend(f'{flow_label}: {e}' for e in schema_errors)
    if schema_errors:
        return errors

    steps = manifest.get('steps') or []
    step_ids: list[str] = []
    known_actions = set(ACTION_REGISTRY.keys())
    allowed = set(manifest.get('allowed_actions') or [])

    for _index, step in enumerate(steps, start=1):
        step_id = step.get('id')
        action = step.get('action')
        if step_id in step_ids:
            errors.append(f'{flow_label}: paso duplicado {step_id}')
        step_ids.append(step_id)
        if action not in known_actions:
            errors.append(f'{flow_label}/{step_id}: acción no registrada {action!r}')
        if allowed and action not in allowed:
            errors.append(f'{flow_label}/{step_id}: acción {action!r} no está en allowed_actions')

    valid_step_ids = set(step_ids)
    for step in steps:
        step_id = step.get('id', '<sin_id>')
        for transition in step.get('transitions', []):
            next_step = transition.get('next')
            if next_step and next_step not in valid_step_ids:
                errors.append(f'{flow_label}/{step_id}: transition apunta a paso inexistente {next_step!r}')

    start_step = manifest.get('start_step')
    if start_step and start_step not in valid_step_ids:
        errors.append(f'{flow_label}: start_step apunta a paso inexistente {start_step!r}')

    return errors


def main() -> None:
    manifests = sorted((ROOT / 'flows').glob('*/manifest.json'))
    errors: list[str] = []
    for manifest_path in manifests:
        try:
            errors.extend(_validate_manifest(manifest_path))
        except Exception as exc:  # noqa: BLE001
            errors.append(f'{manifest_path.parent.name}: no se pudo leer manifest: {exc}')

    result = {
        'ok': not errors,
        'flows_checked': len(manifests),
        'registered_actions': len(list(ACTION_REGISTRY.keys())),
        'errors': errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
