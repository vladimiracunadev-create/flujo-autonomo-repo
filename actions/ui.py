from __future__ import annotations

import shlex
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List


def _import_pyautogui():
    try:
        import pyautogui

        return pyautogui
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            'pyautogui no está disponible o el entorno no permite control de UI. '
            'Instálalo y ejecútalo en un escritorio real.'
        ) from exc


def open_url(url: str, new_tab: bool = True) -> Dict[str, Any]:
    opened = webbrowser.open(url, new=2 if new_tab else 0)
    return {'url': url, 'opened': bool(opened)}


def open_file_in_browser(path: str, new_tab: bool = True) -> Dict[str, Any]:
    target = Path(path).resolve()
    if not target.exists():
        raise FileNotFoundError(f'Archivo no encontrado: {path}')
    opened = webbrowser.open(target.as_uri(), new=2 if new_tab else 0)
    return {'path': str(target), 'opened': bool(opened), 'uri': target.as_uri()}


def launch_process(command: str, wait_seconds: float = 0.0, shell: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    command = command.strip()
    if not command:
        raise ValueError('Se requiere un comando no vacio para lanzar un proceso.')
    if dry_run:
        return {'command': command, 'pid': None, 'launched': False, 'dry_run': True, 'shell': shell}
    if shell:
        process = subprocess.Popen(command, shell=True)
    else:
        process = subprocess.Popen(shlex.split(command), shell=False)
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    return {'command': command, 'pid': process.pid, 'launched': True, 'dry_run': False, 'shell': shell}


def hotkey(keys: List[str], interval: float = 0.0, dry_run: bool = False) -> Dict[str, Any]:
    if dry_run:
        return {'keys': keys, 'sent': False, 'dry_run': True}
    pyautogui = _import_pyautogui()
    pyautogui.hotkey(*keys, interval=interval)
    return {'keys': keys, 'sent': True, 'dry_run': False}


def type_text(text: str, interval: float = 0.01, dry_run: bool = False) -> Dict[str, Any]:
    if dry_run:
        return {'text_length': len(text), 'typed': False, 'dry_run': True, 'preview': text[:200]}
    pyautogui = _import_pyautogui()
    pyautogui.write(text, interval=interval)
    return {'text_length': len(text), 'typed': True, 'dry_run': False}


def click(x: int, y: int, clicks: int = 1, interval: float = 0.0, button: str = 'left', dry_run: bool = False) -> Dict[str, Any]:
    if dry_run:
        return {'x': x, 'y': y, 'clicks': clicks, 'button': button, 'clicked': False, 'dry_run': True}
    pyautogui = _import_pyautogui()
    pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
    return {'x': x, 'y': y, 'clicks': clicks, 'button': button, 'clicked': True, 'dry_run': False}


def click_bbox(bbox: Dict[str, Any], clicks: int = 1, interval: float = 0.0, button: str = 'left', dry_run: bool = False) -> Dict[str, Any]:
    if not bbox:
        raise ValueError('Se requiere un bbox para hacer click visual.')
    left = int(bbox.get('left', 0))
    top = int(bbox.get('top', 0))
    width = int(bbox.get('width', 0))
    height = int(bbox.get('height', 0))
    x = left + max(width // 2, 0)
    y = top + max(height // 2, 0)
    result = click(x=x, y=y, clicks=clicks, interval=interval, button=button, dry_run=dry_run)
    result['bbox'] = bbox
    return result
