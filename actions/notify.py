"""Acción ``notify.send`` con varios backends.

Backends soportados:
- ``log``: imprime a stdout (siempre disponible).
- ``file``: agrega una línea al archivo indicado en ``target``.
- ``webhook``: POST JSON a una URL (Slack/Discord-compatible si la URL acepta ``{"text": "..."}``).

El secreto opcional ``token`` puede pasarse como string literal o como
referencia a un secreto registrado: ``"@secret:NOMBRE"``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.secrets import get_secret


def _resolve_token(token: str | None) -> str | None:
    if not token:
        return None
    if token.startswith('@secret:'):
        return get_secret(token.split(':', 1)[1])
    return token


def send_notification(
    message: str,
    backend: str = 'log',
    target: str | None = None,
    token: str | None = None,
    extra: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        'backend': backend,
        'message': message,
        'timestamp': timestamp,
        'sent': False,
    }

    if backend == 'log':
        print(f'[notify] {timestamp} {message}')
        record['sent'] = True
        return record

    if backend == 'file':
        if not target:
            raise ValueError("backend='file' requiere 'target' (ruta del archivo)")
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as fh:
            fh.write(f'{timestamp}\t{message}\n')
        record['target'] = str(path)
        record['sent'] = True
        return record

    if backend == 'webhook':
        if not target:
            raise ValueError("backend='webhook' requiere 'target' (URL)")
        import requests  # import perezoso para mantener el módulo importable sin requests

        payload: dict[str, Any] = {'text': message, 'timestamp': timestamp}
        if extra:
            payload.update(extra)
        headers: dict[str, str] = {'Content-Type': 'application/json'}
        resolved = _resolve_token(token)
        if resolved:
            headers['Authorization'] = f'Bearer {resolved}'
        response = requests.post(target, json=payload, headers=headers, timeout=timeout)
        record['target'] = target
        record['status_code'] = response.status_code
        record['sent'] = response.ok
        return record

    raise ValueError(f'Backend de notificación no soportado: {backend!r}')
