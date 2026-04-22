from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.database import get_events, get_flow_config, get_run, get_schedule, get_steps, list_runs as db_list_runs


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def flows_dir() -> Path:
    return root_dir() / 'flows'


def list_flow_folders() -> List[Path]:
    return sorted([p for p in flows_dir().iterdir() if p.is_dir()])


def load_manifest(flow_folder: Path) -> Dict[str, Any]:
    return json.loads((flow_folder / 'manifest.json').read_text(encoding='utf-8'))


def list_flows() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for folder in list_flow_folders():
        manifest = load_manifest(folder)
        items.append(
            {
                'folder': folder.name,
                'id': manifest['id'],
                'name': manifest['name'],
                'family': manifest.get('family', 'general'),
                'description': manifest.get('description', ''),
                'steps': manifest.get('steps', []),
                'flow_path': str(folder),
            }
        )
    return items


def get_flow_by_folder(folder_name: str) -> Optional[Dict[str, Any]]:
    folder = flows_dir() / folder_name
    if not folder.exists() or not folder.is_dir():
        return None
    manifest = load_manifest(folder)
    return {
        'folder': folder.name,
        'id': manifest['id'],
        'name': manifest['name'],
        'family': manifest.get('family', 'general'),
        'description': manifest.get('description', ''),
        'steps': manifest.get('steps', []),
        'flow_path': str(folder),
        'readme_path': str(folder / 'README.md'),
        'context_example_path': str(folder / 'context.example.json'),
        'config': get_flow_config(folder.name),
        'schedule': get_schedule(folder.name),
    }


def list_runs(flow_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    return db_list_runs(flow_id=flow_id, limit=limit)


def find_run(flow_id: str, run_id: str) -> Optional[Dict[str, Any]]:
    run = get_run(run_id)
    if not run or run.get('flow_id') != flow_id:
        return None
    return run


def load_run_events(flow_id: str, run_id: str) -> List[Dict[str, Any]]:
    run = get_run(run_id)
    if not run or run.get('flow_id') != flow_id:
        return []
    return get_events(run_id)


def load_run_steps(flow_id: str, run_id: str) -> List[Dict[str, Any]]:
    run = get_run(run_id)
    if not run or run.get('flow_id') != flow_id:
        return []
    return get_steps(run_id)
