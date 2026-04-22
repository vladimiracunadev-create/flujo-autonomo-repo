from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.action_registry import ACTION_REGISTRY  # noqa: E402


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def _validate_manifest(path: Path) -> List[str]:
    errors: List[str] = []
    manifest = _load_json(path)
    flow_label = path.parent.name
    steps = manifest.get('steps')

    if not manifest.get('id'):
        errors.append(f'{flow_label}: falta id')
    if not manifest.get('name'):
        errors.append(f'{flow_label}: falta name')
    if not isinstance(steps, list) or not steps:
        errors.append(f'{flow_label}: steps debe ser una lista no vacia')
        return errors

    step_ids: List[str] = []
    known_actions = set(ACTION_REGISTRY.keys())

    for index, step in enumerate(steps, start=1):
        step_id = step.get('id')
        action = step.get('action')
        if not step_id:
            errors.append(f'{flow_label}: paso #{index} no tiene id')
            continue
        if step_id in step_ids:
            errors.append(f'{flow_label}: paso duplicado {step_id}')
        step_ids.append(step_id)
        if action not in known_actions:
            errors.append(f'{flow_label}/{step_id}: accion no registrada {action!r}')

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
    errors: List[str] = []
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
