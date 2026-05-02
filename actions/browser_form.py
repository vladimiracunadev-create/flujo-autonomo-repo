"""Acción ``browser.fill_form``: abre URL/HTML, rellena formulario y devuelve datos.

Operación avanzada del sistema:
- Carga un dataset JSON de N registros (default ``data/seeds/form_seeds.json``
  con 100 registros).
- Lleva un tracking persistente de IDs ya usados en
  ``data/seeds/.used_indices.json`` para no repetir.
- Elige aleatoriamente uno de los registros NO usados.
- Lanza Chromium (visible o headless) con ``slow_mo`` para que el llenado
  sea visualmente observable.
- Llena los 10 campos del formulario uno por uno.
- Submit, espera la validación JS de la página y devuelve los datos.

NO genera capturas PNG: el output es **solo datos**. El JSON se guarda en
``output/reports/`` (queda en el histórico SQLite del run).

Cuando todos los registros del seed se hayan usado, el tracking se resetea
automáticamente.

Repo upstream: https://github.com/microsoft/playwright-python
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_SEEDS_PATH = 'data/seeds/form_seeds.json'
DEFAULT_USED_PATH = 'data/seeds/.used_indices.json'


def _load_seed_records(seeds_path: str) -> list[dict[str, Any]]:
    p = Path(seeds_path)
    if not p.exists():
        raise FileNotFoundError(
            f'Dataset semilla no encontrado: {seeds_path}. '
            f'Genera el archivo con 100 registros antes de ejecutar el flow.'
        )
    return json.loads(p.read_text(encoding='utf-8'))


def _load_used_ids(used_path: str) -> set[int]:
    p = Path(used_path)
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        return {int(x) for x in data.get('used_ids', [])}
    except (json.JSONDecodeError, ValueError, KeyError):
        return set()


def _save_used_ids(used_path: str, used: set[int], total: int) -> None:
    p = Path(used_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({
            'total_in_dataset': total,
            'used_count': len(used),
            'remaining': total - len(used),
            'used_ids': sorted(used),
        }, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _pick_record(records: list[dict[str, Any]], used_path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Elige un registro no usado al azar. Devuelve (registro, info_tracking)."""
    used = _load_used_ids(used_path)
    available_ids = [r['id'] for r in records if r['id'] not in used]
    cycle_resetted = False
    if not available_ids:
        # Todos usados: reset
        used = set()
        available_ids = [r['id'] for r in records]
        cycle_resetted = True
    chosen_id = random.choice(available_ids)
    used.add(chosen_id)
    _save_used_ids(used_path, used, len(records))
    chosen = next(r for r in records if r['id'] == chosen_id)
    info = {
        'chosen_id': chosen_id,
        'used_count': len(used),
        'remaining': len(records) - len(used),
        'total_in_dataset': len(records),
        'cycle_resetted': cycle_resetted,
    }
    return chosen, info


def _to_url(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme in ('http', 'https', 'file'):
        return target
    candidate = Path(target).resolve()
    if not candidate.exists():
        raise FileNotFoundError(f'Página no encontrada y no es URL válida: {target}')
    return candidate.as_uri()


def fill_form(
    target: str,
    seeds_path: str = DEFAULT_SEEDS_PATH,
    used_path: str = DEFAULT_USED_PATH,
    headless: bool = False,
    slow_mo_ms: int = 250,
    save_data_path: str | None = None,
    viewport_width: int = 1280,
    viewport_height: int = 900,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Carga 100 registros, elige uno NO usado, llena el form y devuelve datos.

    NO genera PNG. Solo datos. El registro elegido queda persistido en
    ``data/seeds/.used_indices.json`` para que la próxima corrida no lo
    repita. Cuando todos se usaron, reset automático.

    Si ``headless=False`` (default) **lanzas una ventana real de Chromium**
    visible. ``slow_mo_ms`` espera N ms entre cada acción para que veas
    cómo se llenan los campos.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'playwright no está instalado. Ejecuta: '
            'pip install playwright && python -m playwright install chromium'
        ) from exc

    records = _load_seed_records(seeds_path)
    chosen, tracking = _pick_record(records, used_path)
    # Filtramos solo las claves que va al formulario (sin 'id' interno)
    form_data = {k: v for k, v in chosen.items() if k != 'id'}

    url = _to_url(target)
    validation_text = ''
    submitted_visible = False
    submitted_payload_text = ''

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=bool(headless), slow_mo=int(slow_mo_ms))
        try:
            context = browser.new_context(
                viewport={'width': int(viewport_width), 'height': int(viewport_height)}
            )
            page = context.new_page()
            page.set_default_timeout(int(timeout_seconds * 1000))
            page.goto(url, wait_until='load')
            page.wait_for_selector('#demo-form')

            # Rellena cada uno de los 10 campos
            for field in ('nombre', 'apellido', 'email', 'telefono', 'direccion',
                          'ciudad', 'fecha_nacimiento', 'profesion', 'comentario'):
                page.fill(f'#{field}', form_data[field])
            page.select_option('#pais', form_data['pais'])

            page.click('#btn-submit')
            try:
                page.wait_for_selector('#validation-result.show', timeout=5000)
                validation_text = (page.text_content('#validation-result') or '').strip()
                submitted_visible = page.is_visible('#submitted-data.show')
                if submitted_visible:
                    submitted_payload_text = (page.text_content('#submitted-data') or '').strip()
            except Exception:
                validation_text = '(timeout esperando #validation-result.show)'
        finally:
            browser.close()

    is_success = validation_text.startswith('✅') or 'válido' in validation_text.lower()

    payload = {
        'url': url,
        'seed_record_id': chosen['id'],
        'tracking': tracking,
        'data_sent': form_data,
        'validation_text': validation_text,
        'is_success': is_success,
        'submitted_visible': submitted_visible,
        'submitted_payload': submitted_payload_text,
    }

    saved_to: str | None = None
    if save_data_path:
        target_save = Path(save_data_path)
        target_save.parent.mkdir(parents=True, exist_ok=True)
        target_save.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        saved_to = str(target_save)

    return {
        'url': url,
        'fields_filled': len(form_data),
        'seed_record_id': chosen['id'],
        'tracking': tracking,
        'data_sent': form_data,
        'validation_text': validation_text,
        'is_success': is_success,
        'submitted_visible': submitted_visible,
        'submitted_payload': submitted_payload_text,
        'saved_to': saved_to,
        'method': 'playwright',
        'headless': bool(headless),
    }
