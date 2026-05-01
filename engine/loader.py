from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from engine.models import FlowDefinition, StepDefinition, TransitionDefinition


class FlowLoader:
    @staticmethod
    def load_manifest(flow_dir: Path) -> FlowDefinition:
        manifest_path = flow_dir / 'manifest.json'
        with manifest_path.open('r', encoding='utf-8') as fh:
            raw = json.load(fh)

        steps = []
        for step in raw['steps']:
            transitions = [
                TransitionDefinition(
                    on=item.get('on', 'success'),
                    next_step=item.get('next'),
                    end=item.get('end', False),
                    when=item.get('when'),
                )
                for item in step.get('transitions', [])
            ]
            steps.append(
                StepDefinition(
                    id=step['id'],
                    action=step['action'],
                    params=step.get('params', {}),
                    save_as=step.get('save_as'),
                    retries=step.get('retries', 0),
                    when=step.get('when'),
                    transitions=transitions,
                )
            )

        return FlowDefinition(
            id=raw['id'],
            name=raw.get('name', raw['id']),
            description=raw.get('description', ''),
            family=raw.get('family', 'general'),
            start_step=raw.get('start_step'),
            max_steps_per_run=int(raw.get('max_steps_per_run', 200)),
            steps=steps,
            allowed_actions=list(raw['allowed_actions']) if raw.get('allowed_actions') else None,
            required_secrets=list(raw.get('required_secrets') or []),
            allowed_paths=list(raw['allowed_paths']) if raw.get('allowed_paths') else None,
            max_runtime_seconds=(
                float(raw['max_runtime_seconds'])
                if raw.get('max_runtime_seconds') is not None
                else None
            ),
        )

    @staticmethod
    def load_context(flow_dir: Path, explicit_context_path: Path | None = None) -> Dict[str, Any]:
        candidates = []
        if explicit_context_path:
            candidates.append(explicit_context_path)
        candidates.extend(
            [
                Path('configs') / f'{flow_dir.name}.json',
                flow_dir / 'context.user.json',
                flow_dir / 'context.example.json',
            ]
        )
        for candidate in candidates:
            if candidate.exists():
                with candidate.open('r', encoding='utf-8') as fh:
                    return json.load(fh)
        return {}
