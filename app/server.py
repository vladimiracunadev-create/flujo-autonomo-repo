from __future__ import annotations

import hmac
import html
import json
import mimetypes
import os.path
import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from engine.catalog import (
    find_run,
    get_flow_by_folder,
    list_flows,
    list_runs,
    load_run_events,
    load_run_steps,
)
from engine.database import (
    get_flow_config,
    get_run,
    get_schedule,
    get_steps,
    init_db,
    set_flow_config,
    set_schedule,
    sync_flows,
)
from engine.metrics import by_flow as metrics_by_flow
from engine.metrics import overview as metrics_overview
from engine.metrics import prometheus_text
from engine.orchestrator import FlowExecutionError, Orchestrator
from engine.paths import root_dir
from engine.scheduler import SchedulerService
from engine.secrets import get_secret

ROOT = root_dir()

# Whitelist estricta para el segmento `folder` proveniente del URL.
# Cierra py/path-injection: cualquier intento de pasar `..`, separadores
# de path, NUL, o caracteres no-ASCII queda rechazado antes de tocar el
# catálogo o el filesystem. Los flows reales usan slug snake_case.
_FOLDER_RE = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')


def _safe_folder(raw: str) -> str | None:
    """Devuelve `raw` si pasa el filtro de slug; si no, None."""
    if not raw or not _FOLDER_RE.match(raw):
        return None
    return raw


def _is_preview(flow: dict) -> bool:
    """True si el flow es preview/no-operativo.

    Dos mecanismos, cualquiera dispara el estado preview:
    1. Campo ``"preview": true`` en el manifest (canónico, viaja con el flow).
    2. Archivo marcador ``.disabled`` en la carpeta del flow (override local
       sin tocar el manifest — útil para deshabilitar temporalmente un flow
       operativo sin commitear cambios).
    """
    flow_path = Path(flow['flow_path'])
    if (flow_path / '.disabled').exists():
        return True
    try:
        manifest = json.loads((flow_path / 'manifest.json').read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(manifest.get('preview'))


def _resolve_under_root(user_path: str) -> Path | None:
    """Resuelve ``user_path`` y garantiza que queda bajo ROOT.

    Devuelve un ``Path`` absoluto seguro o ``None`` si está fuera de ROOT,
    no existe, o la ruta no se puede normalizar. Usa el patrón
    ``realpath`` + ``commonpath`` que CodeQL reconoce como sanitizer
    de py/path-injection.
    """
    if not user_path:
        return None
    root_real = os.path.realpath(str(ROOT))
    base = user_path if os.path.isabs(user_path) else os.path.join(root_real, user_path)
    try:
        target_real = os.path.realpath(base)
        # commonpath lanza ValueError si target/root están en drives
        # distintos (Windows) o si alguno es vacío. Cualquier excepción
        # → tratar como ruta inválida.
        if os.path.commonpath([target_real, root_real]) != root_real:
            return None
    except (OSError, ValueError):
        return None
    return Path(target_real)


SCHEDULER = SchedulerService(loop_sleep_seconds=2.0)
SCHEDULER.start_in_background()
init_db()
sync_flows(list_flows())


def _run_status_payload(run_id: str) -> dict[str, Any]:
    """Estado actual de una corrida con detalle paso a paso.

    Combina la fila de ``runs`` con los registros de ``steps`` y la lista
    completa de pasos del manifest para que el panel pueda mostrar:
    - pasos terminados (success/failed/skipped) con su duración real;
    - el paso "running" actual (primero del manifest sin registro en steps,
      cuando el run sigue activo);
    - los siguientes pasos como "pending".
    """
    run = get_run(run_id)
    if not run:
        return {'ok': False, 'error': 'run no encontrado'}
    steps_records = get_steps(run_id)
    flow = get_flow_by_folder(run['flow_folder'])
    manifest_steps = (flow.get('steps') or []) if flow else []
    by_step_id: dict[str, dict[str, Any]] = {r['step_id']: r for r in steps_records}
    is_running = run['status'] == 'running'
    rendered: list[dict[str, Any]] = []
    found_running = False
    # Cuando el flow ya terminó, los pasos sin record son "rama no tomada"
    # (skipped), no "pendientes" — pending solo aplica a flows aún corriendo.
    fallback_status = 'pending' if is_running else 'not_taken'
    for ms in manifest_steps:
        sid = ms.get('id')
        if not sid:
            continue
        record = by_step_id.get(sid)
        if record:
            rendered.append({
                'step_id': sid,
                'action': record.get('action') or ms.get('action', ''),
                'status': record.get('status'),
                'attempt': record.get('attempt'),
                'duration_seconds': record.get('duration_seconds'),
            })
        elif is_running and not found_running:
            rendered.append({
                'step_id': sid,
                'action': ms.get('action', ''),
                'status': 'running',
                'attempt': None,
                'duration_seconds': None,
            })
            found_running = True
        else:
            rendered.append({
                'step_id': sid,
                'action': ms.get('action', ''),
                'status': fallback_status,
                'attempt': None,
                'duration_seconds': None,
            })
    error_payload = None
    if run.get('error_json'):
        try:
            error_payload = json.loads(run['error_json'])
        except json.JSONDecodeError:
            error_payload = run['error_json']
    return {
        'ok': True,
        'run_id': run_id,
        'flow_id': run.get('flow_id'),
        'flow_folder': run.get('flow_folder'),
        'flow_name': run.get('flow_name'),
        'status': run.get('status'),
        'steps': rendered,
        'duration_seconds': run.get('duration_seconds'),
        'started_at': run.get('started_at'),
        'finished_at': run.get('finished_at'),
        'error': error_payload,
    }


PAGE_CSS = '''
:root {
  --bg: #f4f7fb;
  --surface: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --accent: #2563eb;
  --accent-soft: #dbeafe;
  --success: #166534;
  --success-soft: #dcfce7;
  --danger: #991b1b;
  --danger-soft: #fee2e2;
  --running: #1d4ed8;
  --running-soft: #dbeafe;
  --border: #e5e7eb;
  --shadow: 0 10px 26px rgba(15, 23, 42, .07);
  --radius: 16px;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  margin: 0; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased;
}
header.top {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: white; padding: 22px 28px; box-shadow: var(--shadow);
}
header.top .row { max-width: 1340px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
header.top h1 { margin: 0; font-size: 22px; font-weight: 600; }
header.top .sub { color: #94a3b8; font-size: 13px; margin-top: 4px; }
header.top a { color: #cbd5e1; text-decoration: none; font-size: 14px; }
header.top a:hover { color: white; text-decoration: underline; }
header.top .nav { display: flex; gap: 18px; }
main { padding: 24px; max-width: 1340px; margin: 0 auto; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

.tabs {
  display: flex; gap: 4px; border-bottom: 2px solid var(--border);
  margin-bottom: 22px; overflow-x: auto;
}
.tab-btn {
  background: transparent; border: none; padding: 12px 20px;
  font-size: 15px; font-weight: 600; color: var(--muted);
  cursor: pointer; border-bottom: 3px solid transparent;
  margin-bottom: -2px; display: inline-flex; align-items: center; gap: 8px;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-btn .count { background: var(--accent-soft); color: var(--accent); padding: 2px 8px; border-radius: 999px; font-size: 12px; }
.tab-pane { display: none; }
.tab-pane.active { display: block; }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
.card {
  background: var(--surface); border-radius: var(--radius); padding: 20px;
  box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 8px;
  border: 1px solid var(--border); transition: transform .12s ease, box-shadow .12s ease;
}
.card:hover { transform: translateY(-1px); box-shadow: 0 14px 32px rgba(15,23,42,.10); }
.card h3 { margin: 4px 0 2px; font-size: 17px; }
.card .muted { color: var(--muted); font-size: 13px; line-height: 1.5; min-height: 38px; }
.card .meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; font-size: 12px; }
.card .meta span { background: #f1f5f9; padding: 4px 10px; border-radius: 999px; color: #475569; }
.card .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }

button, .button {
  border: none; border-radius: 10px; padding: 9px 16px; font-size: 14px; font-weight: 500;
  cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;
  transition: background .12s ease, transform .06s ease;
}
button:active, .button:active { transform: translateY(1px); }
.button.primary, button.primary { background: var(--accent); color: white; }
.button.primary:hover, button.primary:hover { background: #1d4ed8; }
.button.secondary, button.secondary { background: #e2e8f0; color: var(--text); }
.button.secondary:hover, button.secondary:hover { background: #cbd5e1; }
.button.ghost, button.ghost { background: transparent; color: var(--muted); border: 1px solid var(--border); }
.button.ghost:hover, button.ghost:hover { background: #f1f5f9; }
.button.danger, button.danger { background: var(--danger-soft); color: var(--danger); }
button[disabled] { opacity: .55; cursor: not-allowed; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 500; }
.badge.completed { background: var(--success-soft); color: var(--success); }
.badge.failed { background: var(--danger-soft); color: var(--danger); }
.badge.running { background: var(--running-soft); color: var(--running); }
.badge.idle { background: #f1f5f9; color: var(--muted); }
.badge.scheduled { background: #fef3c7; color: #92400e; }
.dot { width: 6px; height: 6px; border-radius: 999px; background: currentColor; }

table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); }
th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); vertical-align: middle; font-size: 14px; }
th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
tbody tr:hover { background: #f8fafc; }
tbody tr:last-child td { border-bottom: none; }

.path { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: var(--muted); word-break: break-all; }
pre { background: #0f172a; color: #e2e8f0; padding: 14px; border-radius: 12px; overflow: auto; font-size: 12px; line-height: 1.5; max-width: 100%; white-space: pre-wrap; word-break: break-word; }

input[type=text], input[type=number], textarea, select {
  font-family: inherit; font-size: 14px; padding: 9px 12px;
  border: 1px solid var(--border); border-radius: 10px; background: white; width: 100%;
}
input:focus, textarea:focus, select:focus { outline: 2px solid var(--accent-soft); border-color: var(--accent); }
textarea { font-family: ui-monospace, monospace; min-height: 240px; }
label { display: block; font-size: 13px; font-weight: 500; color: var(--muted); margin: 12px 0 6px; }

.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }
.toolbar input { max-width: 320px; }

.toast { position: fixed; bottom: 20px; right: 20px; background: var(--text); color: white; padding: 12px 18px; border-radius: 10px; box-shadow: var(--shadow); z-index: 9999; opacity: 0; transform: translateY(8px); transition: opacity .2s ease, transform .2s ease; max-width: 360px; }
.toast.show { opacity: 1; transform: translateY(0); }
.toast.error { background: var(--danger); }
.toast.success { background: var(--success); }

.empty { text-align: center; padding: 48px 24px; color: var(--muted); }
.empty h4 { margin: 0 0 6px; color: var(--text); }

.thumb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.thumb { background: #f1f5f9; border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }
.thumb img { width: 100%; height: 130px; object-fit: cover; display: block; }
.thumb .label { padding: 8px 10px; font-size: 12px; color: var(--muted); border-top: 1px solid var(--border); background: white; word-break: break-all; }

.two-col { display: grid; grid-template-columns: 1.1fr .9fr; gap: 18px; }
.two-col > div { min-width: 0; }
table { table-layout: auto; }
table td, table th { word-break: break-word; }
table.steps td:last-child { max-width: 320px; }
table.steps td:last-child pre { max-height: 200px; overflow: auto; }
@media (max-width: 960px) { .two-col { grid-template-columns: 1fr; } }

.spinner { width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

.live-status { font-size: 12px; color: var(--muted); margin-top: 10px; min-height: 16px; }

.kbd-hint { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--muted); margin-left: auto; }
kbd { display: inline-block; padding: 2px 7px; background: #f1f5f9; border: 1px solid #cbd5e1; border-bottom-width: 2px; border-radius: 5px; font-family: ui-monospace, monospace; font-size: 11px; color: #334155; }

.modal-bg { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,.55); display: flex; align-items: center; justify-content: center; z-index: 9000; }
.modal { background: white; border-radius: 16px; max-width: 540px; width: 90%; max-height: 86vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,.25); }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.modal-head h3 { margin: 0; font-size: 18px; }
.modal-head button { background: transparent; border: none; font-size: 18px; cursor: pointer; color: var(--muted); padding: 4px 10px; }
.modal-body { padding: 16px 20px; }
.modal-body h4 { margin: 0 0 8px; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.kbd-row { display: flex; align-items: center; gap: 12px; padding: 6px 0; font-size: 13px; }
.kbd-row kbd { min-width: 70px; text-align: center; }

/* === Run detail / Flow info === */
.hero-card { background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%); border: none; }
.hero-image-card { padding: 0; overflow: hidden; cursor: zoom-in; margin-top: 16px; transition: transform .15s ease; }
.hero-image-card:hover { transform: translateY(-2px); box-shadow: 0 18px 40px rgba(15,23,42,.12); }
.hero-image-card img { width: 100%; max-height: 520px; object-fit: contain; display: block; background: #0f172a; }
.hero-image-meta { padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }

.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); }
.kpi-num { font-size: 28px; font-weight: 700; margin-top: 6px; }

.run-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.run-tile { background: white; border: 1px solid var(--border); border-radius: 14px; overflow: hidden; text-decoration: none; color: inherit; transition: transform .12s ease, box-shadow .12s ease; display: flex; flex-direction: column; }
.run-tile:hover { transform: translateY(-2px); box-shadow: 0 14px 32px rgba(15,23,42,.10); text-decoration: none; }
.run-tile-preview { background: #0f172a; height: 140px; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.run-tile-preview img { width: 100%; height: 100%; object-fit: cover; }
.run-tile-meta { padding: 10px 12px; }
.run-tile-status { font-size: 12px; }
.json-thumb { display: flex; flex-direction: column; align-items: center; justify-content: center; color: #94a3b8; gap: 8px; }
.json-thumb .json-icon { font-size: 36px; }
.json-thumb .json-keys { font-family: ui-monospace, monospace; font-size: 11px; max-width: 90%; text-align: center; word-break: break-all; }

.smart-summary { display: flex; flex-direction: column; gap: 0; }
.smart-row { display: grid; grid-template-columns: 180px 1fr; gap: 14px; padding: 10px 0; border-bottom: 1px solid var(--border); align-items: center; font-size: 13px; }
.smart-row:last-child { border-bottom: none; }
.smart-key { font-weight: 600; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }
.rgb-swatch { display: inline-block; width: 16px; height: 16px; border-radius: 4px; vertical-align: middle; margin-right: 6px; border: 1px solid var(--border); }
.compact-list { margin: 0; padding-left: 18px; font-size: 13px; }
.compact-list li { margin: 2px 0; }
.mini-table { margin-top: 10px; }
.mini-table th, .mini-table td { padding: 6px 10px; font-size: 12px; }

.meta-details { background: white; border: 1px solid var(--border); border-radius: 12px; padding: 0; box-shadow: var(--shadow); }
.meta-details summary { padding: 14px 18px; cursor: pointer; font-weight: 600; color: var(--text); user-select: none; }
.meta-details summary:hover { background: #f8fafc; }
.meta-details[open] summary { border-bottom: 1px solid var(--border); }
.meta-details pre { margin: 14px; }

table.steps.clickable tbody tr { cursor: pointer; }
table.steps.clickable tbody tr:hover { background: #eff6ff; }

.lightbox { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.85); z-index: 9500; cursor: zoom-out; align-items: center; justify-content: center; padding: 24px; }
.lightbox.show { display: flex; }
.lightbox img { max-width: 95%; max-height: 95%; box-shadow: 0 20px 80px rgba(0,0,0,.5); border-radius: 8px; }
.lightbox .lb-caption { position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%); color: white; font-family: ui-monospace, monospace; font-size: 12px; background: rgba(0,0,0,.5); padding: 6px 14px; border-radius: 999px; }

.run-progress { background: #f8fafc; border-radius: 12px; padding: 12px; border: 1px solid var(--border); }
.run-progress-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; gap: 8px; }
.run-progress-header a { font-size: 12px; }
.step-list { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.step-row { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; gap: 8px; align-items: center; padding: 6px 8px; border-radius: 8px; background: white; border: 1px solid var(--border); font-size: 12px; min-width: 0; }
.step-row .step-meta { display: flex; gap: 8px; align-items: center; min-width: 0; }
.step-row .step-meta > * { white-space: nowrap; }
.step-row .step-icon { text-align: center; font-weight: 600; font-size: 14px; color: var(--muted); }
.step-row .step-name { font-weight: 600; color: var(--text); }
.step-row .step-action { font-size: 11px; }
.step-row .step-status { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; padding: 2px 8px; border-radius: 999px; background: #f1f5f9; }
.step-row.step-success { background: #f0fdf4; border-color: #bbf7d0; }
.step-row.step-success .step-icon { color: var(--success); }
.step-row.step-success .step-status { background: var(--success-soft); color: var(--success); }
.step-row.step-failed { background: #fef2f2; border-color: #fecaca; }
.step-row.step-failed .step-icon { color: var(--danger); }
.step-row.step-failed .step-status { background: var(--danger-soft); color: var(--danger); }
.step-row.step-running { background: #eff6ff; border-color: #bfdbfe; animation: pulse 1.4s ease-in-out infinite; }
.step-row.step-running .step-icon { color: var(--running); }
.step-row.step-running .step-status { background: var(--running-soft); color: var(--running); }
.step-row.step-skipped { background: #f8fafc; opacity: 0.7; }
.step-row.step-skipped .step-icon { color: var(--muted); }
.step-row.step-not_taken { background: #f8fafc; opacity: 0.55; border-style: dashed; }
.step-row.step-not_taken .step-icon { color: var(--muted); }
.step-row.step-not_taken .step-status { background: #e2e8f0; color: var(--muted); }
.step-row.step-pending { opacity: 0.55; }
.step-error { margin-top: 8px; padding: 8px 10px; background: var(--danger-soft); color: var(--danger); border-radius: 8px; font-size: 12px; }
@keyframes pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, .25); } 50% { box-shadow: 0 0 0 6px rgba(37, 99, 235, 0); } }
'''


PAGE_JS = '''
function showTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.dataset.tab === name));
  if (history.replaceState) history.replaceState(null, '', '#' + name);
}
function showToast(msg, kind) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show ' + (kind || '');
  setTimeout(() => el.classList.remove('show'), 3500);
}
function statusIcon(s) {
  if (s === 'success' || s === 'completed') return '✓';
  if (s === 'failed') return '✕';
  if (s === 'skipped') return '⏭';
  if (s === 'not_taken') return '⊘';
  if (s === 'running') return '⏳';
  return '○';
}
function renderProgress(payload) {
  const steps = payload.steps || [];
  const lines = steps.map(s => {
    const icon = statusIcon(s.status);
    const dur = s.duration_seconds != null ? `<span class="muted">${Number(s.duration_seconds).toFixed(2)}s</span>` : '';
    return `<div class="step-row step-${s.status}">
      <span class="step-icon">${icon}</span>
      <span class="step-name" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><strong>${s.step_id}</strong> <span class="path" style="margin-left:6px">${s.action}</span></span>
      <span class="step-meta"><span class="step-status">${s.status}</span> ${dur}</span>
    </div>`;
  }).join('');
  return `<div class="step-list">${lines}</div>`;
}
async function pollStatus(runId, card, btn, flowId) {
  const status = card.querySelector('.live-status');
  let stop = false;
  let consecutiveErrors = 0;
  while (!stop) {
    try {
      const res = await fetch('/api/runs/' + encodeURIComponent(runId) + '/status');
      const data = await res.json();
      if (!data.ok) { consecutiveErrors++; if (consecutiveErrors > 5) break; await new Promise(r => setTimeout(r, 700)); continue; }
      consecutiveErrors = 0;
      const isTerminal = data.status === 'completed' || data.status === 'failed';
      const headerCls = data.status === 'completed' ? 'completed' : (data.status === 'failed' ? 'failed' : 'running');
      const detailLink = `/run/${flowId}/${runId}`;
      const _esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      const _errText = data.error ? (typeof data.error === 'string' ? data.error : (data.error.message || JSON.stringify(data.error))) : '';
      const errBlock = _errText ? `<div class="step-error">${_esc(_errText)}</div>` : '';
      status.innerHTML = `<div class="run-progress">
        <div class="run-progress-header">
          <span class="badge ${headerCls}"><span class="dot"></span>${_esc(data.status)}</span>
          <a href="${detailLink}">ver detalle →</a>
        </div>
        ${renderProgress(data)}
        ${errBlock}
      </div>`;
      if (isTerminal) {
        stop = true;
        btn.disabled = false;
        btn.textContent = 'Ejecutar de nuevo';
        showToast('Flow terminó: ' + data.status, data.status === 'completed' ? 'success' : 'error');
        break;
      }
    } catch (e) {
      consecutiveErrors++;
      if (consecutiveErrors > 5) break;
    }
    await new Promise(r => setTimeout(r, 700));
  }
}
function askFolderForFlow03() {
  return new Promise(resolve => {
    const suggestions = ['data/inbox', 'data/dropbox/inbox', 'output/reports', 'output/screenshots', 'docs', 'flows'];
    const sugBtns = suggestions.map(s =>
      `<button type="button" class="ghost" style="font-size:12px;padding:4px 10px"
         onclick="document.getElementById('folder-input').value='${s}'">${s}</button>`
    ).join(' ');
    const html = `<div id="folder-modal" class="modal-bg">
      <div class="modal" onclick="event.stopPropagation()">
        <div class="modal-head"><h3>📁 ¿Qué carpeta querés explorar?</h3>
          <button onclick="document.getElementById('folder-modal').remove();window._flow03Resolve&&window._flow03Resolve(null)">✕</button></div>
        <div class="modal-body">
          <p style="margin-top:0;color:var(--muted);font-size:13px">Escribí la ruta relativa al workspace (data/...) o absoluta (C:\\\\Users\\\\...).</p>
          <input id="folder-input" type="text" placeholder="data/inbox" value="data/inbox" style="width:100%" autofocus />
          <div style="margin-top:10px">
            <div style="font-size:12px;color:var(--muted);margin-bottom:6px">Sugerencias rápidas:</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">${sugBtns}</div>
          </div>
          <div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">
            <button class="ghost" onclick="document.getElementById('folder-modal').remove();window._flow03Resolve&&window._flow03Resolve(null)">Cancelar</button>
            <button class="primary" id="folder-submit">Ejecutar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
    const input = document.getElementById('folder-input');
    const submit = document.getElementById('folder-submit');
    window._flow03Resolve = (val) => { window._flow03Resolve = null; resolve(val); };
    const accept = () => {
      const v = (input.value || '').trim();
      document.getElementById('folder-modal').remove();
      window._flow03Resolve(v || null);
    };
    submit.addEventListener('click', accept);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); accept(); }
      if (e.key === 'Escape') { e.preventDefault(); document.getElementById('folder-modal').remove(); window._flow03Resolve(null); }
    });
    setTimeout(() => input.focus(), 50);
  });
}
function askUrlForFlow02() {
  return new Promise(resolve => {
    const html = `<div id="url-modal" class="modal-bg">
      <div class="modal" onclick="event.stopPropagation()">
        <div class="modal-head"><h3>🌐 ¿Qué página querés capturar?</h3>
          <button onclick="document.getElementById('url-modal').remove();window._flow02Resolve&&window._flow02Resolve(null)">✕</button></div>
        <div class="modal-body">
          <p style="margin-top:0;color:var(--muted);font-size:13px">Pega una URL completa (https://...) o una ruta local relativa al workspace (data/web/control_page.html).</p>
          <input id="url-input" type="text" placeholder="https://example.com  o  data/web/control_page.html" value="data/web/control_page.html"
            style="width:100%" autofocus />
          <div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">
            <button class="ghost" onclick="document.getElementById('url-modal').remove();window._flow02Resolve&&window._flow02Resolve(null)">Cancelar</button>
            <button class="primary" id="url-submit">Capturar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
    const input = document.getElementById('url-input');
    const submit = document.getElementById('url-submit');
    window._flow02Resolve = (val) => { window._flow02Resolve = null; resolve(val); };
    const accept = () => {
      const v = (input.value || '').trim();
      document.getElementById('url-modal').remove();
      window._flow02Resolve(v || null);
    };
    submit.addEventListener('click', accept);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); accept(); }
      if (e.key === 'Escape') { e.preventDefault(); document.getElementById('url-modal').remove(); window._flow02Resolve(null); }
    });
    setTimeout(() => input.focus(), 50);
  });
}
async function runFlow(folder, btn, opts) {
  opts = opts || {};
  const card = btn ? btn.closest('.flow-card') : document.querySelector('.flow-card[data-folder="' + folder + '"]');
  if (!card) return;
  if (!btn) btn = card.querySelector('button.primary');
  const status = card.querySelector('.live-status');
  // Caso especial flow 12: tomar la URL del input inline si existe;
  // si vino por atajo (opts.fromShortcut) y no hay input visible, abrir modal.
  let body = null;
  if (folder === '02_screen_capture_browser') {
    const inlineInput = card.querySelector('.flow02-url');
    let url = inlineInput ? (inlineInput.value || '').trim() : '';
    if (!url || opts.fromShortcut) {
      url = await askUrlForFlow02();
      if (!url) return;
    }
    body = JSON.stringify({ context_overrides: { target_url: url } });
  }
  if (folder === '03_folder_inventory') {
    const inlineInput = card.querySelector('.flow03-folder');
    let path = inlineInput ? (inlineInput.value || '').trim() : '';
    if (!path || opts.fromShortcut) {
      path = await askFolderForFlow03();
      if (!path) return;
    }
    body = JSON.stringify({ context_overrides: { path_override: path } });
  }
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Iniciando…';
  status.innerHTML = '<span class="badge running"><span class="dot"></span>iniciando</span>';
  try {
    const fetchOpts = { method: 'POST' };
    if (body) { fetchOpts.headers = {'Content-Type': 'application/json'}; fetchOpts.body = body; }
    const res = await fetch('/api/run/' + encodeURIComponent(folder), fetchOpts);
    const data = await res.json();
    if (data.ok && data.run_id) {
      btn.innerHTML = '<span class="spinner"></span> En curso…';
      pollStatus(data.run_id, card, btn, data.flow_id);
    } else {
      const _escErr = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      status.innerHTML = `<span class="badge failed"><span class="dot"></span>error</span> ${_escErr(data.error || '')}`;
      showToast('Error: ' + (data.error || 'desconocido'), 'error');
      btn.disabled = false;
      btn.textContent = 'Ejecutar';
    }
  } catch (e) {
    status.innerHTML = `<span class="badge failed"><span class="dot"></span>error de red</span>`;
    showToast('Error de red', 'error');
    btn.disabled = false;
    btn.textContent = 'Ejecutar';
  }
}
function filterTable(inputId, tbodyId) {
  const q = (document.getElementById(inputId).value || '').toLowerCase();
  document.querySelectorAll('#' + tbodyId + ' tr').forEach(tr => {
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}
window.addEventListener('DOMContentLoaded', () => {
  const hash = (location.hash || '#run').replace('#', '');
  if (['run','schedule','history'].includes(hash)) showTab(hash);
});

// === Atajos de teclado ===
// Alt+1..9, Alt+0 (=10), Alt+- (=11), Alt+= (=12) → ejecuta flow N
// Alt+H → tab Histórico, Alt+P → tab Programadas, Alt+E → tab Ejecutar
// Alt+M → /metrics/dashboard
// ? o F1 → modal de ayuda
const KEY_TO_INDEX = {
  '1':0,'2':1,'3':2,'4':3,'5':4,'6':5,'7':6,'8':7,'9':8,
  '0':9,'-':10,'=':11
};
function openImageLightbox(url, name) {
  const lb = document.getElementById('lightbox');
  if (!lb) return;
  const _e = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  lb.innerHTML = `<img src="${_e(url)}" alt="${_e(name||'')}" /><div class="lb-caption">${_e(name||'')}</div>`;
  lb.classList.add('show');
}
function closeLightbox() {
  const lb = document.getElementById('lightbox');
  if (lb) lb.classList.remove('show');
}
function showStepResult(index, row) {
  const dataEl = row.querySelector('.step-data');
  if (!dataEl) return;
  const raw = dataEl.textContent;
  let pretty = raw;
  try { pretty = JSON.stringify(JSON.parse(raw), null, 2); } catch {}
  const stepName = row.querySelector('strong')?.textContent || '';
  const action = row.querySelector('.path')?.textContent || '';
  const html = `<div class="modal-bg" id="step-result-modal" onclick="this.remove()">
    <div class="modal" onclick="event.stopPropagation()" style="max-width:780px">
      <div class="modal-head">
        <h3>Paso ${index} · <span class="path">${stepName}</span></h3>
        <button onclick="document.getElementById('step-result-modal').remove()">✕</button>
      </div>
      <div class="modal-body">
        <div class="muted" style="margin-bottom:10px;font-size:12px">Acción: <span class="path">${action}</span></div>
        <pre style="max-height:60vh;overflow:auto">${pretty.replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))}</pre>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}
function closeStepModal() { const m = document.getElementById('step-result-modal'); if (m) m.remove(); }
function showShortcutsHelp() {
  const existing = document.getElementById('shortcuts-modal');
  if (existing) { existing.remove(); return; }
  const cards = document.querySelectorAll('.flow-card');
  const items = Array.from(cards).slice(0, 12).map((c, i) => {
    const folder = c.getAttribute('data-folder') || '';
    const name = c.querySelector('h3')?.textContent || folder;
    const labels = ['Alt+1','Alt+2','Alt+3','Alt+4','Alt+5','Alt+6','Alt+7','Alt+8','Alt+9','Alt+0','Alt+-','Alt+='];
    return `<div class="kbd-row"><kbd>${labels[i]}</kbd><span>${name}</span></div>`;
  }).join('');
  const html = `<div id="shortcuts-modal" class="modal-bg" onclick="this.remove()">
    <div class="modal" onclick="event.stopPropagation()">
      <div class="modal-head"><h3>⌨️ Atajos de teclado</h3><button onclick="document.getElementById('shortcuts-modal').remove()">✕</button></div>
      <div class="modal-body">
        <h4>Ejecutar flow</h4>
        ${items}
        <h4 style="margin-top:14px">Navegación</h4>
        <div class="kbd-row"><kbd>Alt+E</kbd><span>Tab Ejecutar</span></div>
        <div class="kbd-row"><kbd>Alt+P</kbd><span>Tab Programadas</span></div>
        <div class="kbd-row"><kbd>Alt+H</kbd><span>Tab Histórico</span></div>
        <div class="kbd-row"><kbd>Alt+M</kbd><span>Dashboard de Métricas</span></div>
        <div class="kbd-row"><kbd>?</kbd><span>Mostrar/ocultar esta ayuda</span></div>
        <div class="kbd-row"><kbd>Esc</kbd><span>Cerrar este modal</span></div>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}
document.addEventListener('keydown', e => {
  // Modal close con Esc
  if (e.key === 'Escape') {
    const m = document.getElementById('shortcuts-modal');
    if (m) { m.remove(); e.preventDefault(); return; }
  }
  // Help con ? o F1
  if ((e.key === '?' && !e.ctrlKey && !e.metaKey) || e.key === 'F1') {
    e.preventDefault();
    showShortcutsHelp();
    return;
  }
  // Solo procesamos Alt + tecla
  if (!e.altKey || e.ctrlKey || e.metaKey) return;
  // No interferir con inputs
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea') return;

  // Alt+E/P/H/M = navegación
  const navKey = e.key.toLowerCase();
  if (navKey === 'e') { e.preventDefault(); showTab('run'); return; }
  if (navKey === 'p') { e.preventDefault(); showTab('schedule'); return; }
  if (navKey === 'h') { e.preventDefault(); showTab('history'); return; }
  if (navKey === 'm') { e.preventDefault(); location.href = '/metrics/dashboard'; return; }

  // Alt+1..9, Alt+0, Alt+-, Alt+= = ejecutar flow N
  if (KEY_TO_INDEX.hasOwnProperty(e.key)) {
    const idx = KEY_TO_INDEX[e.key];
    const cards = document.querySelectorAll('.flow-card');
    if (idx < cards.length) {
      const card = cards[idx];
      const folder = card.getAttribute('data-folder');
      e.preventDefault();
      showTab('run');
      card.scrollIntoView({behavior: 'smooth', block: 'center'});
      // Preview cards (.disabled marker) no se ejecutan ni por atajo ni por click
      if (card.getAttribute('data-preview') === 'true') {
        showToast('🚧 Flow ' + (idx + 1) + ' en preview — aún no operativo');
        return;
      }
      runFlow(folder, null, { fromShortcut: true });
      showToast('▶ Atajo Alt+' + e.key + ' → flow ' + (idx + 1));
    }
  }
});
'''


def html_page(title: str, body: str, active_nav: str = '') -> bytes:
    page = f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<header class="top">
  <div class="row">
    <div>
      <h1>Automa</h1>
      <div class="sub">Orquestador local · panel operativo</div>
    </div>
    <div class="nav">
      <a href="/">Inicio</a>
      <a href="/metrics/dashboard">Métricas</a>
      <a href="/api/metrics">API</a>
    </div>
  </div>
</header>
<main>{body}</main>
<div id="toast" class="toast"></div>
<script>{PAGE_JS}</script>
</body>
</html>'''
    return page.encode('utf-8')


def badge(status: str) -> str:
    cls = {
        'completed': 'completed', 'failed': 'failed', 'running': 'running',
    }.get(status, 'idle')
    return f'<span class="badge {cls}"><span class="dot"></span>{html.escape(status)}</span>'


def safe_json_loads(text: str | None):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


_SHORTCUT_LABELS = ['Alt+1','Alt+2','Alt+3','Alt+4','Alt+5','Alt+6','Alt+7','Alt+8','Alt+9','Alt+0','Alt+-','Alt+=']


def _flow_card_run_tab(flow: dict, latest: dict | None, index: int) -> str:
    status_html = badge(latest['status']) + f' · <a href="/run/{flow["id"]}/{latest["run_id"]}">último run</a>' if latest else '<span class="muted">sin ejecuciones aún</span>'
    shortcut = _SHORTCUT_LABELS[index] if index < len(_SHORTCUT_LABELS) else ''
    shortcut_html = f'<span class="kbd-hint"><kbd>{shortcut}</kbd></span>' if shortcut else ''

    preview = _is_preview(flow)
    preview_badge_html = (
        '<span class="badge idle" title="Caso en preview — declarado en el catálogo pero aún no operativo. Ver docs/ROADMAP.md."><span class="dot"></span>🚧 preview</span>'
        if preview else ''
    )
    if preview:
        run_button_html = (
            '<button class="ghost" disabled title="Caso en preview — aún no operativo. Roadmap: docs/ROADMAP.md">🚧 Preview · no operativo</button>'
        )
    else:
        run_button_html = f'<button class="primary" onclick="runFlow(\'{flow["folder"]}\', this)">Ejecutar</button>'

    # Caso especial: flow 02 (browser) lleva input inline para la URL a capturar
    # Caso especial: flow 03 (inventory) lleva input inline para la carpeta a explorar
    inline_input_html = ''
    if flow['folder'] == '02_screen_capture_browser':
        inline_input_html = '''
      <div style="margin-top:10px">
        <label style="font-size:12px;color:var(--muted);margin:0 0 4px 0">🌐 URL o ruta local a capturar</label>
        <input class="flow02-url" type="text" placeholder="https://example.com  o  data/web/control_page.html"
               value="data/web/control_page.html" style="font-size:13px" />
      </div>
        '''
    elif flow['folder'] == '03_folder_inventory':
        inline_input_html = '''
      <div style="margin-top:10px">
        <label style="font-size:12px;color:var(--muted);margin:0 0 4px 0">📁 Carpeta a explorar</label>
        <input class="flow03-folder" type="text" placeholder="data/inbox  o  C:\\\\Users\\\\..."
               value="data/inbox" style="font-size:13px" />
      </div>
        '''

    return f'''
    <div class="card flow-card" data-folder="{html.escape(flow['folder'])}" data-preview="{'true' if preview else 'false'}">
      <div class="meta">
        <span>{html.escape(flow.get('family','general'))}</span>
        <span>{len(flow.get('steps',[]))} pasos</span>
        {shortcut_html}
        {preview_badge_html}
      </div>
      <h3>{html.escape(flow['name'])}</h3>
      <div class="muted">{html.escape(flow['description'] or '')}</div>
      <div class="meta"><span class="path">{html.escape(flow['folder'])}</span></div>
      {inline_input_html}
      <div class="actions">
        {run_button_html}
        <a class="button ghost" href="/flow/{flow['folder']}">Detalle</a>
      </div>
      <div class="live-status">{status_html}</div>
    </div>
    '''


def _flow_card_schedule_tab(flow: dict, schedule: dict) -> str:
    enabled = bool(int(schedule.get('enabled') or 0))
    status_pill = (
        '<span class="badge scheduled"><span class="dot"></span>activo</span>'
        if enabled else '<span class="badge idle"><span class="dot"></span>inactivo</span>'
    )
    cron = html.escape(str(schedule.get('cron_expression') or ''))
    interval = html.escape(str(schedule.get('interval_seconds') or 60))
    next_run = html.escape(str(schedule.get('next_run_at') or '—'))
    last_run = html.escape(str(schedule.get('last_run_at') or '—'))
    return f'''
    <div class="card">
      <div class="meta"><span>{html.escape(flow.get('family','general'))}</span> {status_pill}</div>
      <h3>{html.escape(flow['name'])}</h3>
      <form method="post" action="/flow/{flow['folder']}/schedule" style="margin-top:8px">
        <label><input type="checkbox" name="enabled" {'checked' if enabled else ''}/> Activar scheduler</label>
        <label>Intervalo (segundos) — si no usas cron</label>
        <input type="number" min="1" name="interval_seconds" value="{interval}" />
        <label>Expresión cron (5 campos: min hora dom mes dow)</label>
        <input type="text" name="cron_expression" value="{cron}" placeholder="*/15 * * * *" />
        <div class="actions"><button class="primary" type="submit">Guardar</button>
          <a class="button ghost" href="/flow/{flow['folder']}/config">Editar contexto</a>
        </div>
        <div class="meta" style="margin-top:10px">
          <span>Próxima: {next_run}</span>
          <span>Última: {last_run}</span>
        </div>
      </form>
    </div>
    '''


def _history_row(run: dict) -> str:
    duration = run.get('duration_seconds')
    duration_text = f'{round(duration, 2)}s' if duration is not None else '—'
    return (
        f"<tr>"
        f"<td><span class='path'>{html.escape(run['run_id'])}</span></td>"
        f"<td>{html.escape(run['flow_name'])}</td>"
        f"<td>{badge(run['status'])}</td>"
        f"<td>{html.escape(str(run.get('created_at') or ''))}</td>"
        f"<td>{duration_text}</td>"
        f"<td><a class='button ghost' href='/run/{run['flow_id']}/{run['run_id']}'>Ver</a></td>"
        f"</tr>"
    )


def render_home() -> bytes:
    flows = list_flows()
    runs = list_runs(limit=200)
    runs_by_flow: dict = {}
    for run in runs:
        runs_by_flow.setdefault(run['flow_id'], []).append(run)

    run_cards = ''.join(_flow_card_run_tab(flow, (runs_by_flow.get(flow['id']) or [None])[0], idx) for idx, flow in enumerate(flows))
    schedule_cards = ''.join(_flow_card_schedule_tab(flow, get_schedule(flow['folder'])) for flow in flows)
    history_rows = ''.join(_history_row(run) for run in runs) or '<tr><td colspan="6" class="empty">Sin corridas todavía. Ejecuta un flow para empezar.</td></tr>'

    active_count = sum(1 for f in flows if int(get_schedule(f['folder']).get('enabled') or 0))
    total_runs = len(runs)

    body = f'''
    <div class="tabs" role="tablist" style="display:flex;align-items:center">
      <button class="tab-btn active" data-tab="run" onclick="showTab('run')">▶ Ejecutar <span class="count">{len(flows)}</span></button>
      <button class="tab-btn" data-tab="schedule" onclick="showTab('schedule')">⏰ Programadas <span class="count">{active_count}</span></button>
      <button class="tab-btn" data-tab="history" onclick="showTab('history')">📜 Histórico <span class="count">{total_runs}</span></button>
      <button class="tab-btn" style="margin-left:auto" onclick="showShortcutsHelp()" title="Ver atajos de teclado">⌨️ <kbd style="margin-left:4px">?</kbd></button>
    </div>

    <div class="tab-pane active" data-tab="run">
      <div class="card" style="margin-bottom:16px;background:linear-gradient(135deg,#eff6ff 0%,#f5f3ff 100%);border:none">
        <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
          <div style="flex:1">
            <h3 style="margin:0">Ejecuta cualquier proceso con un clic</h3>
            <div class="muted" style="margin-top:4px">Las salidas se guardan automáticamente en <span class="path">output/</span> y el detalle queda en el histórico.</div>
          </div>
        </div>
      </div>
      <div class="grid">{run_cards}</div>
    </div>

    <div class="tab-pane" data-tab="schedule">
      <div class="card" style="margin-bottom:16px;background:linear-gradient(135deg,#fff7ed 0%,#fef3c7 100%);border:none">
        <div>
          <h3 style="margin:0">Programa las mismas acciones</h3>
          <div class="muted" style="margin-top:4px">Usa intervalo en segundos o una expresión cron de 5 campos. El scheduler local persiste en SQLite y respeta el lock por flow.</div>
        </div>
      </div>
      <div class="grid">{schedule_cards}</div>
    </div>

    <div class="tab-pane" data-tab="history">
      <div class="toolbar">
        <input id="hist-search" type="text" placeholder="Filtrar por flow, run id, estado…" oninput="filterTable('hist-search','hist-tbody')" />
        <span class="muted">{total_runs} corridas registradas</span>
      </div>
      <table>
        <thead><tr><th>Run</th><th>Flow</th><th>Estado</th><th>Creado</th><th>Duración</th><th></th></tr></thead>
        <tbody id="hist-tbody">{history_rows}</tbody>
      </table>
    </div>
    '''
    return html_page('Centro de procesos · Automa', body, active_nav='home')


def _run_first_image(run: dict) -> dict | None:
    """Devuelve el primer output PNG/JPG del run, si lo hay."""
    outs = safe_json_loads(run.get('outputs_json')) or []
    for o in outs:
        if isinstance(o, dict):
            p = (o.get('path') or '').lower()
            if p.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                return o
    return None


def _run_first_json_output(run: dict) -> dict | None:
    outs = safe_json_loads(run.get('outputs_json')) or []
    for o in outs:
        if isinstance(o, dict) and (o.get('path') or '').lower().endswith('.json'):
            return o
    return None


def render_flow_info(folder: str) -> bytes:
    """Dashboard específico de un flow: hero + historial visual + meta colapsable."""
    flow = get_flow_by_folder(folder)
    if not flow:
        return html_page('No encontrado', '<div class="empty"><h4>Flujo inexistente</h4><a class="button ghost" href="/">Volver</a></div>')
    readme = Path(flow['readme_path']).read_text(encoding='utf-8') if Path(flow['readme_path']).exists() else ''
    manifest = Path(flow['flow_path']) / 'manifest.json'
    manifest_text = manifest.read_text(encoding='utf-8')
    runs = list_runs(flow['id'], limit=24)
    schedule = get_schedule(folder)

    total_runs = len(runs)
    completed = sum(1 for r in runs if r.get('status') == 'completed')
    failed = sum(1 for r in runs if r.get('status') == 'failed')
    avg_duration = (
        sum(r.get('duration_seconds') or 0 for r in runs if r.get('duration_seconds') is not None)
        / max(1, sum(1 for r in runs if r.get('duration_seconds') is not None))
    ) if runs else 0

    # Grid visual de últimas corridas
    if runs:
        cards_html = []
        for r in runs[:12]:
            img = _run_first_image(r)
            jsn = _run_first_json_output(r)
            run_id = r['run_id']
            status = r.get('status') or 'unknown'
            dur = r.get('duration_seconds')
            dur_text = f'{round(dur, 2)}s' if dur is not None else '—'
            created = (r.get('created_at') or '')[:19].replace('T', ' ')
            preview_html = ''
            if img:
                file_url = f"/file?path={html.escape(img['path'])}"
                preview_html = f'<a href="{file_url}" target="_blank"><img src="{file_url}" loading="lazy" /></a>'
            elif jsn:
                # Lee unas claves del JSON para mostrar como preview
                try:
                    data = json.loads(Path(jsn['path']).read_text(encoding='utf-8'))
                    keys = list(data.keys())[:3]
                    preview_html = '<div class="json-thumb"><div class="json-icon">📊</div><div class="json-keys">' + ' · '.join(html.escape(k) for k in keys) + '</div></div>'
                except Exception:
                    preview_html = '<div class="json-thumb"><div class="json-icon">📊</div><div class="json-keys">JSON</div></div>'
            else:
                preview_html = '<div class="json-thumb"><div class="json-icon">○</div><div class="json-keys">sin output</div></div>'
            cards_html.append(f'''
              <a class="run-tile" href="/run/{flow["id"]}/{run_id}">
                <div class="run-tile-preview">{preview_html}</div>
                <div class="run-tile-meta">
                  <div class="run-tile-status">{badge(status)} <span class="muted" style="margin-left:6px">{dur_text}</span></div>
                  <div class="muted" style="font-size:11px;margin-top:4px">{html.escape(created)}</div>
                </div>
              </a>
            ''')
        history_visual = '<div class="run-grid">' + ''.join(cards_html) + '</div>'
    else:
        history_visual = '<div class="empty"><h4>Aún no hay corridas</h4><div>Ejecuta el flow para ver el historial visual aquí.</div></div>'

    enabled = bool(int(schedule.get('enabled') or 0))
    schedule_text = (
        f'⏰ Cada {schedule["interval_seconds"]}s' if enabled and schedule.get('interval_seconds') and not schedule.get('cron_expression') else
        f'⏰ cron: {html.escape(schedule["cron_expression"])}' if enabled and schedule.get('cron_expression') else
        '🔕 sin scheduler'
    )

    body = f'''
    <div class="toolbar">
      <a class="button ghost" href="/">← Volver al inicio</a>
      <a class="button ghost" href="/flow/{flow['folder']}/config">⚙️ Configurar</a>
    </div>

    <div class="card hero-card">
      <div class="meta">
        <span>{html.escape(flow.get('family','general'))}</span>
        <span>{len(flow.get('steps',[]))} pasos</span>
        <span class="path">{html.escape(flow['folder'])}</span>
      </div>
      <h2 style="margin:6px 0">{html.escape(flow['name'])}</h2>
      <p class="muted" style="margin:0 0 12px 0;font-size:14px;line-height:1.55">{html.escape(flow['description'] or '')}</p>
      <div class="actions">
        <button class="primary flow-card" onclick="runFlow('{flow['folder']}', this)" data-folder="{flow['folder']}">▶ Ejecutar ahora</button>
        <a class="button secondary" href="/flow/{flow['folder']}/config">Editar configuración</a>
      </div>
      <div class="live-status"></div>
    </div>

    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(180px,1fr));margin:18px 0">
      <div class="kpi-card"><div class="muted">Corridas registradas</div><div class="kpi-num">{total_runs}</div></div>
      <div class="kpi-card"><div class="muted">Completadas</div><div class="kpi-num" style="color:var(--success)">{completed}</div></div>
      <div class="kpi-card"><div class="muted">Falladas</div><div class="kpi-num" style="color:var(--danger)">{failed}</div></div>
      <div class="kpi-card"><div class="muted">Duración promedio</div><div class="kpi-num">{round(avg_duration, 2)}s</div></div>
      <div class="kpi-card"><div class="muted">Programación</div><div style="margin-top:6px;font-size:13px">{schedule_text}</div></div>
    </div>

    <div class="card">
      <h3 style="margin-top:0">📜 Historial visual de este flow</h3>
      <p class="muted" style="margin:0 0 14px 0">Mostrando últimas {min(12, total_runs)} corridas. Click sobre una para ver detalle completo de esa ejecución.</p>
      {history_visual}
    </div>

    <details class="meta-details" style="margin-top:18px">
      <summary>📋 README del caso (clic para mostrar)</summary>
      <pre>{html.escape(readme)}</pre>
    </details>

    <details class="meta-details" style="margin-top:8px">
      <summary>🛠️ Manifest completo (JSON declarativo)</summary>
      <pre>{html.escape(manifest_text)}</pre>
    </details>
    '''
    return html_page(f'{flow["name"]} · Automa', body)


def render_flow_config(folder: str, message: str = '') -> bytes:
    flow = get_flow_by_folder(folder)
    if not flow:
        return html_page('No encontrado', '<div class="empty"><h4>Flujo inexistente</h4></div>')
    current = get_flow_config(folder)
    if current is None:
        current_path = Path(flow['context_example_path'])
        current = json.loads(current_path.read_text(encoding='utf-8')) if current_path.exists() else {}
    schedule = get_schedule(folder)
    enabled = bool(int(schedule.get('enabled') or 0))
    msg_html = f'<div class="card" style="background:var(--success-soft);border-color:#bbf7d0;color:var(--success)">{html.escape(message)}</div>' if message else ''
    body = f'''
    <div class="toolbar"><a class="button ghost" href="/">← Volver</a></div>
    {msg_html}
    <div class="two-col">
      <div class="card">
        <h3>Configuración del flujo</h3>
        <div class="muted">Lo que guardes aquí será el contexto operativo por defecto del caso.</div>
        <form method="post" action="/flow/{folder}/config">
          <label>JSON del contexto</label>
          <textarea name="config_json">{html.escape(json.dumps(current, ensure_ascii=False, indent=2))}</textarea>
          <div class="actions"><button class="primary" type="submit">Guardar configuración</button></div>
        </form>
      </div>
      <div class="card">
        <h3>Scheduler</h3>
        <form method="post" action="/flow/{folder}/schedule">
          <label><input type="checkbox" name="enabled" {'checked' if enabled else ''}/> Activar scheduler</label>
          <label>Intervalo en segundos</label>
          <input type="number" min="1" name="interval_seconds" value="{html.escape(str(schedule.get('interval_seconds') or 60))}" />
          <label>Expresión cron (5 campos: min hora dom mes dow)</label>
          <input type="text" name="cron_expression" value="{html.escape(str(schedule.get('cron_expression') or ''))}" placeholder="*/15 * * * *" />
          <div class="actions"><button class="primary" type="submit">Guardar scheduler</button></div>
        </form>
        <div class="meta" style="margin-top:12px">
          <span>Próxima: {html.escape(str(schedule.get('next_run_at') or '—'))}</span>
          <span>Última: {html.escape(str(schedule.get('last_run_at') or '—'))}</span>
        </div>
      </div>
    </div>
    '''
    return html_page(f'Configurar · {flow["name"]}', body)


def render_flow_history(folder: str) -> bytes:
    flow = get_flow_by_folder(folder)
    if not flow:
        return html_page('No encontrado', '<div class="empty"><h4>Flujo inexistente</h4></div>')
    runs = list_runs(flow['id'], limit=100)
    rows = ''.join(_history_row(r) for r in runs) or '<tr><td colspan="6" class="empty">Sin corridas</td></tr>'
    body = f'''
    <div class="toolbar"><a class="button ghost" href="/">← Volver</a></div>
    <div class="card">
      <h3>Histórico — {html.escape(flow['name'])}</h3>
      <table>
        <thead><tr><th>Run</th><th>Flow</th><th>Estado</th><th>Creado</th><th>Duración</th><th></th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    '''
    return html_page(f'Histórico · {flow["name"]}', body)


def _output_thumb(item: dict) -> str:
    path = item.get('path', '')
    name = item.get('name', path)
    is_image = path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
    file_url = f"/file?path={html.escape(path)}"
    if is_image:
        return f'''
        <div class="thumb">
          <a href="{file_url}" target="_blank"><img src="{file_url}" alt="{html.escape(name)}" loading="lazy" /></a>
          <div class="label">{html.escape(name)}</div>
        </div>
        '''
    return f'''
    <div class="thumb">
      <div style="height:130px;display:flex;align-items:center;justify-content:center;background:white;color:var(--muted);font-size:32px">📄</div>
      <div class="label"><a href="{file_url}" target="_blank">{html.escape(name)}</a></div>
    </div>
    '''


def _smart_summary(flow_id: str, context: dict, outputs: list) -> str:
    """Resumen inteligente y legible según el flow ejecutado.

    Genera un bloque HTML específico para cada tipo de flow, mostrando los
    datos relevantes en lenguaje humano en vez de un dump JSON crudo.
    """
    parts: list[str] = []
    if flow_id == 'screen_capture_analyze':
        cap = context.get('capture') or {}
        ana = context.get('analysis') or {}
        parts.append(f'<div class="smart-row"><span class="smart-key">Resolución</span><span>{cap.get("width","?")}×{cap.get("height","?")}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Método</span><span class="path">{cap.get("method","?")}</span></div>')
        if ana.get('analyzer'):
            parts.append(f'<div class="smart-row"><span class="smart-key">Analizador</span><span class="path">{ana.get("analyzer")}</span></div>')
        if ana.get('avg_brightness') is not None:
            parts.append(f'<div class="smart-row"><span class="smart-key">Brillo promedio</span><span>{ana.get("avg_brightness")}/255</span></div>')
        if ana.get('mean_rgb'):
            r, g, b = ana['mean_rgb'][:3]
            parts.append(f'<div class="smart-row"><span class="smart-key">RGB promedio</span><span><span class="rgb-swatch" style="background:rgb({int(r)},{int(g)},{int(b)})"></span> ({r}, {g}, {b})</span></div>')
        if ana.get('visual_state'):
            parts.append(f'<div class="smart-row"><span class="smart-key">Estado visual</span><span><strong>{ana.get("visual_state")}</strong></span></div>')
    elif flow_id == 'screen_capture_browser':
        cap = context.get('capture') or {}
        parts.append(f'<div class="smart-row"><span class="smart-key">URL capturada</span><span class="path">{html.escape(str(cap.get("url","")))}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Título de página</span><span>{html.escape(str(cap.get("title","")))}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Viewport</span><span>{cap.get("width","?")}×{cap.get("height","?")}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Página completa</span><span>{"sí" if cap.get("full_page") else "solo viewport"}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Tamaño PNG</span><span>{round((cap.get("size_bytes",0) or 0)/1024,1)} KB</span></div>')
    elif flow_id == 'folder_inventory':
        inv = context.get('inventory') or {}
        st = context.get('stats') or {}
        parts.append(f'<div class="smart-row"><span class="smart-key">Carpeta</span><span class="path">{html.escape(str(inv.get("path","")))}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Archivos</span><span><strong>{inv.get("total_files",0)}</strong></span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Tamaño total</span><span>{round((st.get("total_size_bytes",0) or 0)/1024,2)} KB</span></div>')
        by_ext = st.get('by_extension') or {}
        if by_ext:
            ext_str = ' · '.join(f'<code>{html.escape(k)}</code> ×{v}' for k, v in sorted(by_ext.items()))
            parts.append(f'<div class="smart-row"><span class="smart-key">Por extensión</span><span>{ext_str}</span></div>')
        if st.get('largest_file'):
            lf = st['largest_file']
            parts.append(f'<div class="smart-row"><span class="smart-key">Archivo mayor</span><span>{html.escape(str(lf.get("name","")))} ({lf.get("size_bytes",0)} B)</span></div>')
    elif flow_id == 'document_drop_pipeline':
        inv = context.get('inventory') or {}
        summ = (context.get('summary') or {}).get('summaries') or []
        parts.append(f'<div class="smart-row"><span class="smart-key">Carpeta procesada</span><span class="path">{html.escape(str(inv.get("path","")))}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Archivos leídos</span><span>{len(summ)}</span></div>')
        if summ:
            files_html = ''.join(f'<li><strong>{html.escape(s.get("name",""))}</strong> <span class="muted">({s.get("chars",0)} chars · {s.get("line_count",0)} líneas)</span></li>' for s in summ[:10])
            parts.append(f'<div class="smart-row"><span class="smart-key">Lista</span><span><ul class="compact-list">{files_html}</ul></span></div>')
    elif flow_id == 'system_healthcheck':
        snap = context.get('snapshot') or {}
        dec = context.get('decision') or {}
        parts.append(f'<div class="smart-row"><span class="smart-key">CPU</span><span><strong>{snap.get("cpu_percent","?")}%</strong></span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Memoria</span><span><strong>{snap.get("memory_percent","?")}%</strong> ({round((snap.get("memory_used_mb") or 0)/1024,2)} GB usados)</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Disco</span><span><strong>{snap.get("disk_percent","?")}%</strong> ({snap.get("disk_used_gb","?")} GB)</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Plataforma</span><span class="path">{html.escape(str(snap.get("platform","?")))}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Decisión</span><span><strong>{html.escape(str(dec.get("status","?")))}</strong></span></div>')
    elif flow_id == 'process_watchdog':
        top = (context.get('top') or {}).get('processes') or []
        watch = context.get('watch') or {}
        parts.append(f'<div class="smart-row"><span class="smart-key">Procesos vistos</span><span>{(context.get("top") or {}).get("total_seen",0)}</span></div>')
        parts.append(f'<div class="smart-row"><span class="smart-key">Alertas</span><span><strong>{watch.get("alert_count",0)}</strong> superan umbrales</span></div>')
        if top:
            top_html = ''.join(
                f'<tr><td><strong>{html.escape(str(p.get("name","")))}</strong></td>'
                f'<td><span class="path">PID {p.get("pid","")}</span></td>'
                f'<td>{p.get("memory_mb",0)} MB</td>'
                f'<td>{p.get("cpu_percent",0)}%</td></tr>'
                for p in top[:10]
            )
            parts.append(f'<table class="mini-table"><thead><tr><th>Proceso</th><th>PID</th><th>Memoria</th><th>CPU</th></tr></thead><tbody>{top_html}</tbody></table>')
    return ''.join(parts) if parts else ''


def render_run_detail(flow_id: str, run_id: str) -> bytes:
    run = find_run(flow_id, run_id)
    if not run:
        return html_page('No encontrado', '<div class="empty"><h4>Corrida inexistente</h4><a class="button ghost" href="/">Volver</a></div>')
    steps = load_run_steps(flow_id, run_id)
    events = load_run_events(flow_id, run_id)
    context = safe_json_loads(run.get('context_json')) or {}
    outputs = safe_json_loads(run.get('outputs_json')) or []
    error = safe_json_loads(run.get('error_json'))

    # Imagen prominente (si hay)
    primary_image = None
    other_outputs: list[dict] = []
    for o in outputs:
        if not isinstance(o, dict) or not o.get('path'):
            continue
        if (o.get('path') or '').lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) and primary_image is None:
            primary_image = o
        else:
            other_outputs.append(o)

    hero_image_html = ''
    if primary_image:
        file_url = f"/file?path={html.escape(primary_image['path'])}"
        size_kb = round((primary_image.get('size_bytes', 0) or 0) / 1024, 1)
        hero_image_html = f'''
        <div class="card hero-image-card" onclick="openImageLightbox('{file_url}', '{html.escape(primary_image["name"])}')">
          <img src="{file_url}" alt="{html.escape(primary_image["name"])}" loading="lazy" />
          <div class="hero-image-meta">
            <span class="path">{html.escape(primary_image["name"])}</span>
            <span class="muted">{size_kb} KB · click para ver en grande</span>
          </div>
        </div>
        '''

    # Resumen inteligente (legible humano)
    smart_html = _smart_summary(flow_id, context, outputs)
    smart_block = f'<div class="card" style="margin-top:16px"><h3 style="margin-top:0">📊 Qué pasó en esta corrida</h3><div class="smart-summary">{smart_html}</div></div>' if smart_html else ''

    # Steps row con click para ver resultado completo
    step_rows = ''
    for index, step in enumerate(steps, start=1):
        result = safe_json_loads(step.get('result_json')) or step.get('error_text') or ''
        result_str = json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, (dict, list)) else str(result)
        result_short = result_str[:140] + ('…' if len(result_str) > 140 else '')
        step_rows += (
            f'<tr onclick="showStepResult({index}, this)">'
            f'<td>{index}</td>'
            f'<td><strong>{html.escape(step["step_id"])}</strong></td>'
            f'<td><span class="path">{html.escape(step["action"])}</span></td>'
            f'<td>{badge(step["status"])}</td>'
            f'<td>{round(step.get("duration_seconds") or 0, 3)}s</td>'
            f'<td><span class="muted">{html.escape(result_short)}</span></td>'
            f'<td><script type="application/json" class="step-data">{html.escape(result_str)}</script><span class="muted" style="font-size:11px">▼</span></td>'
            f'</tr>'
        )
    if not step_rows:
        step_rows = '<tr><td colspan="7" class="empty">Sin pasos</td></tr>'

    # Otras salidas (no la imagen hero)
    other_thumbs_html = ''.join(_output_thumb(item) for item in other_outputs)

    # Eventos colapsables
    event_lines = []
    for event in events:
        payload = safe_json_loads(event.get('payload_json'))
        event_lines.append({'event_time': event.get('event_time'), 'event_type': event.get('event_type'), 'payload': payload})

    duration = run.get('duration_seconds')
    duration_text = f'{round(duration, 3)} s' if duration is not None else '—'
    created = (run.get('created_at') or '')[:19].replace('T', ' ')

    body = f'''
    <div class="toolbar">
      <a class="button ghost" href="/">← Inicio</a>
      <a class="button ghost" href="/flow/{run.get('flow_folder', '')}">📋 Ver historial completo de {html.escape(run['flow_name'])}</a>
    </div>

    <div class="card hero-card">
      <div class="meta">{badge(run['status'])} <span>{html.escape(run['flow_name'])}</span></div>
      <h2 style="margin:6px 0 8px 0">Resultado de la corrida</h2>
      <div class="meta">
        <span class="path">{html.escape(run['run_id'])}</span>
        <span>⏱️ {duration_text}</span>
        <span>📅 {html.escape(created)}</span>
      </div>
      {('<div style="margin-top:12px;padding:12px 16px;background:var(--danger-soft);border-radius:10px;color:var(--danger)"><strong>Error:</strong> ' + html.escape(json.dumps(error, ensure_ascii=False)) + '</div>') if error else ''}
    </div>

    {hero_image_html}
    {smart_block}

    {f'<div class="card" style="margin-top:16px"><h3 style="margin-top:0">📂 Otros archivos generados</h3><div class="thumb-grid">{other_thumbs_html}</div></div>' if other_thumbs_html else ''}

    <div class="card" style="margin-top:16px">
      <h3 style="margin-top:0">⚙️ Pasos ejecutados</h3>
      <p class="muted" style="margin:0 0 10px 0;font-size:12px">Click en una fila para ver el resultado completo del paso.</p>
      <table class="steps clickable">
        <thead><tr><th>#</th><th>Paso</th><th>Acción</th><th>Estado</th><th>Duración</th><th>Resultado (preview)</th><th></th></tr></thead>
        <tbody id="steps-tbody">{step_rows}</tbody>
      </table>
    </div>

    <details class="meta-details" style="margin-top:14px">
      <summary>📋 Datos finales completos del contexto (JSON)</summary>
      <pre>{html.escape(json.dumps(context, ensure_ascii=False, indent=2))}</pre>
    </details>

    <details class="meta-details" style="margin-top:8px">
      <summary>🔧 Eventos técnicos detallados ({len(event_lines)} eventos)</summary>
      <pre>{html.escape(json.dumps(event_lines, ensure_ascii=False, indent=2))}</pre>
    </details>

    <div id="lightbox" class="lightbox" onclick="closeLightbox()"></div>
    <div id="step-modal" class="modal-bg" style="display:none" onclick="closeStepModal()"></div>
    '''
    return html_page(f'Run {run_id}', body)


def render_metrics_dashboard() -> bytes:
    overview = metrics_overview()
    flows = metrics_by_flow()
    totals = overview.get('totals_by_status') or {}
    rows = ''.join(
        f"<tr><td>{html.escape(item['flow_id'])}</td><td>{item['runs_total']}</td>"
        f"<td>{item['runs_completed']}</td><td>{item['runs_failed']}</td>"
        f"<td>{round(item['avg_duration_seconds'] or 0, 3)}s</td>"
        f"<td>{html.escape(str(item.get('last_run_at') or ''))}</td></tr>"
        for item in flows
    ) or '<tr><td colspan="6" class="empty">Sin corridas</td></tr>'
    slowest = ''.join(
        f"<tr><td><span class='path'>{html.escape(row['action'])}</span></td><td>{round(row['avg_d'] or 0, 3)}s</td><td>{row['c']}</td></tr>"
        for row in (overview.get('slowest_actions') or [])
    ) or '<tr><td colspan="3" class="empty">Sin datos</td></tr>'
    retries = ''.join(
        f"<tr><td><span class='path'>{html.escape(row['action'])}</span></td><td>{row['retry_count']}</td></tr>"
        for row in (overview.get('retries_top_actions') or [])
    ) or '<tr><td colspan="2" class="empty">Sin retries</td></tr>'
    body = f'''
    <div class="toolbar"><a class="button ghost" href="/">← Volver</a></div>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr));margin-bottom:16px">
      <div class="card"><div class="muted">Completadas</div><h3 style="font-size:32px;margin:4px 0;color:var(--success)">{totals.get('completed',0)}</h3></div>
      <div class="card"><div class="muted">Falladas</div><h3 style="font-size:32px;margin:4px 0;color:var(--danger)">{totals.get('failed',0)}</h3></div>
      <div class="card"><div class="muted">En curso</div><h3 style="font-size:32px;margin:4px 0;color:var(--running)">{totals.get('running',0)}</h3></div>
      <div class="card"><div class="muted">Duración promedio</div><h3 style="font-size:32px;margin:4px 0">{round(overview.get('average_duration_seconds') or 0, 2)}s</h3></div>
    </div>
    <div class="two-col">
      <div class="card">
        <h3>Por flow</h3>
        <table><thead><tr><th>Flow</th><th>Total</th><th>OK</th><th>Fail</th><th>Avg</th><th>Última</th></tr></thead><tbody>{rows}</tbody></table>
      </div>
      <div>
        <div class="card">
          <h3>Acciones más lentas</h3>
          <table><thead><tr><th>Acción</th><th>Avg</th><th>Muestras</th></tr></thead><tbody>{slowest}</tbody></table>
        </div>
        <div class="card" style="margin-top:16px">
          <h3>Acciones con más reintentos</h3>
          <table><thead><tr><th>Acción</th><th>Retries</th></tr></thead><tbody>{retries}</tbody></table>
        </div>
      </div>
    </div>
    '''
    return html_page('Métricas · Automa', body)


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # silencia logs ruidosos
        return

    def _send_html(self, content: bytes, status: int = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = HTTPStatus.OK, content_type: str = 'text/plain; charset=utf-8') -> None:
        body = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', location)
        self.end_headers()

    def _read_form(self):
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length).decode('utf-8') if length else ''
        return parse_qs(raw)

    # --- Auth helpers ---------------------------------------------------
    #
    # Modelo de protección de endpoints mutadores (POST que disparan flows,
    # editan config, programan scheduler, escriben en disco):
    #
    #   1. Si el operador define AUTOMA_PANEL_TOKEN, **toda** mutación exige
    #      el header `X-Automa-Token` con valor exacto (comparación constant-
    #      time vía hmac.compare_digest, CWE-208).
    #
    #   2. Si no hay token configurado (modo "panel local sin fricción"),
    #      se aplican defensas anti-CSRF y anti-DNS-rebinding:
    #        a. El header `Host` debe ser loopback (127.0.0.1/localhost).
    #        b. Si la request trae `Origin`, debe igualar `http://<Host>`.
    #        c. Si trae `Referer`, debe empezar con `http://<Host>/`.
    #      Esto bloquea el caso real: un sitio web malicioso que el usuario
    #      visita y que intenta `fetch('http://127.0.0.1:8787/api/run/X')`
    #      — el browser siempre envía Origin en cross-site fetch.
    #
    #   3. El webhook entrante (/api/hook/) sigue exigiendo
    #      AUTOMA_WEBHOOK_TOKEN siempre (es la única superficie diseñada
    #      para llamadas no-locales).

    def _check_token(self, env_name: str) -> bool:
        expected = get_secret(env_name)
        if not expected:
            return False
        provided = self.headers.get('X-Automa-Token', '')
        if not provided:
            return False
        return hmac.compare_digest(provided, expected)

    def _check_webhook_token(self) -> bool:
        return self._check_token('AUTOMA_WEBHOOK_TOKEN')

    def _authorize_mutation(self) -> tuple[bool, str]:
        """Devuelve (ok, error_msg) para endpoints mutadores."""
        # Modo 1: token explícito configurado.
        panel_token = get_secret('AUTOMA_PANEL_TOKEN')
        if panel_token:
            if self._check_token('AUTOMA_PANEL_TOKEN'):
                return True, ''
            return False, 'token inválido (AUTOMA_PANEL_TOKEN requerido)'

        # Modo 2: sin token, exigir loopback + Origin/Referer consistentes.
        host = (self.headers.get('Host') or '').strip()
        host_only = host.split(':', 1)[0].lower()
        if host_only not in {'127.0.0.1', 'localhost', '[::1]', '::1'}:
            return False, 'Host no loopback: cliente remoto debe usar AUTOMA_PANEL_TOKEN'

        expected_origin = f'http://{host}'
        origin = self.headers.get('Origin')
        if origin and origin != expected_origin:
            return False, f'Origin {origin!r} no coincide con {expected_origin!r}'

        referer = self.headers.get('Referer')
        if referer and not referer.startswith(expected_origin + '/') and referer != expected_origin:
            return False, f'Referer {referer!r} no coincide con {expected_origin!r}'

        return True, ''

    def _reject_unauthorized(self, error_msg: str, *, as_json: bool) -> None:
        payload = {'ok': False, 'error': f'no autorizado: {error_msg}'}
        if as_json:
            self._send_json(payload, status=HTTPStatus.UNAUTHORIZED)
        else:
            self._send_html(
                html_page('No autorizado', f'<div class="empty"><h4>401</h4><p>{html.escape(error_msg)}</p></div>'),
                status=HTTPStatus.UNAUTHORIZED,
            )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/':
            return self._send_html(render_home())
        if path == '/healthz':
            return self._send_json({'status': 'ok'})
        if path == '/metrics':
            return self._send_text(prometheus_text(), content_type='text/plain; version=0.0.4; charset=utf-8')
        if path == '/api/metrics':
            return self._send_json({'overview': metrics_overview(), 'by_flow': metrics_by_flow()})
        if path == '/metrics/dashboard':
            return self._send_html(render_metrics_dashboard())
        if path == '/api/flows':
            return self._send_json(list_flows())
        if path == '/api/runs':
            params = parse_qs(parsed.query)
            flow_id = params.get('flow_id', [None])[0]
            limit = int(params.get('limit', ['50'])[0])
            return self._send_json(list_runs(flow_id=flow_id, limit=limit))
        if path.startswith('/api/runs/') and path.endswith('/status'):
            run_id = path[len('/api/runs/'):-len('/status')]
            return self._send_json(_run_status_payload(run_id))
        if path.startswith('/flow/'):
            parts = [p for p in path.split('/') if p]
            folder = _safe_folder(parts[1] if len(parts) > 1 else '')
            if folder is None:
                return self._send_html(html_page('Folder inválido', '<div class="empty"><h4>Folder inválido</h4></div>'), status=400)
            if len(parts) == 2:
                return self._send_html(render_flow_info(folder))
            if len(parts) == 3 and parts[2] == 'config':
                return self._send_html(render_flow_config(folder))
            if len(parts) == 3 and parts[2] == 'history':
                return self._send_html(render_flow_history(folder))
        if path.startswith('/run/'):
            parts = [p for p in path.split('/') if p]
            if len(parts) == 3:
                return self._send_html(render_run_detail(parts[1], parts[2]))
        if path == '/file':
            params = parse_qs(parsed.query)
            rel = unquote(params.get('path', [''])[0])
            # Anti path-traversal (CWE-22). Patrón inline reconocido por
            # CodeQL py/path-injection (ver ejemplo canónico de la regla):
            # normalizar el path JOIN-eado y exigir prefijo absoluto.
            if not rel:
                return self._send_html(html_page('Archivo no encontrado', '<div class="empty"><h4>Ruta inválida</h4></div>'), status=404)
            # Allowlist mínima de caracteres en el path relativo, antes de
            # tocar el filesystem. Bloquea NUL bytes y otros chars raros.
            if '\x00' in rel or any(ord(c) < 32 for c in rel):
                return self._send_html(html_page('Archivo no encontrado', '<div class="empty"><h4>Ruta inválida</h4></div>'), status=404)
            base_path = os.path.realpath(str(ROOT))
            # Rechazamos paths absolutos: el cliente pide siempre rutas
            # relativas a la raíz del proyecto. Esto simplifica el sanitizer
            # y elimina el caso `C:\Windows\System32`.
            if os.path.isabs(rel):
                return self._send_html(html_page('Archivo no encontrado', '<div class="empty"><h4>Ruta inválida</h4></div>'), status=404)
            fullpath = os.path.normpath(os.path.join(base_path, rel))
            # Patrón canónico CodeQL: startswith sobre prefijo absoluto.
            # Sumamos os.sep para cerrar el bypass por sibling-prefix
            # (`/.../repo-evil` startswith `/.../repo`).
            if not fullpath.startswith(base_path + os.sep):
                return self._send_html(html_page('Archivo no encontrado', '<div class="empty"><h4>Ruta inválida</h4></div>'), status=404)
            if not os.path.isfile(fullpath):
                return self._send_html(html_page('Archivo no encontrado', '<div class="empty"><h4>Ruta inválida</h4></div>'), status=404)
            # Allowlist de extensiones: bloqueamos contenido ejecutable por
            # browser desde el mismo origen (CWE-79 reflejada).
            ext = os.path.splitext(fullpath)[1].lower()
            if ext in {'.html', '.htm', '.xhtml', '.xml', '.svg', '.js', '.mjs', '.css'}:
                return self._send_html(html_page('Tipo no permitido', '<div class="empty"><h4>Extensión no servida</h4></div>'), status=415)
            mime, _ = mimetypes.guess_type(fullpath)
            with open(fullpath, 'rb') as fh:
                content = fh.read()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', mime or 'application/octet-stream')
            self.send_header('Content-Length', str(len(content)))
            # Endurece el sniffing: el browser no debe "adivinar" tipos.
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(content)
            return
        return self._send_html(html_page('No encontrado', '<div class="empty"><h4>Ruta inexistente</h4><a class="button ghost" href="/">Volver</a></div>'), status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        # /api/hook/ tiene su propio mecanismo de auth (token webhook); todo
        # el resto pasa por _authorize_mutation (anti-CSRF/DNS-rebinding).
        if path != '/api/hook/' and not path.startswith('/api/hook/'):
            ok, err = self._authorize_mutation()
            if not ok:
                as_json = path.startswith('/api/')
                return self._reject_unauthorized(err, as_json=as_json)
        if path == '/api/form/submit':
            length = int(self.headers.get('Content-Length', '0') or '0')
            if length <= 0:
                return self._send_json({'ok': False, 'error': 'sin body'}, status=400)
            raw = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return self._send_json({'ok': False, 'error': 'JSON inválido'}, status=400)
            from datetime import datetime as _dt
            ts = _dt.now().strftime('%Y%m%d_%H%M%S_%f')
            target = ROOT / 'output' / 'reports' / f'form_submission_panel_{ts}.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            return self._send_json({'ok': True, 'saved_path': str(target.relative_to(ROOT))})
        if path.startswith('/api/run/'):
            folder = _safe_folder(path[len('/api/run/'):].strip('/'))
            if folder is None:
                return self._send_json({'ok': False, 'error': 'folder inválido'}, status=400)
            flow = get_flow_by_folder(folder)
            if not flow:
                return self._send_json({'ok': False, 'error': 'flow no encontrado'}, status=404)
            if _is_preview(flow):
                return self._send_json({'ok': False, 'error': 'flow en preview — aún no operativo (ver docs/ROADMAP.md)'}, status=409)
            # Lee overrides del body (JSON) si los hay
            overrides: dict[str, Any] = {}
            length = int(self.headers.get('Content-Length', '0') or '0')
            if length > 0:
                raw = self.rfile.read(length).decode('utf-8')
                try:
                    body = json.loads(raw)
                    if isinstance(body, dict) and isinstance(body.get('context_overrides'), dict):
                        overrides = body['context_overrides']
                except json.JSONDecodeError:
                    pass
            # Run async: instanciamos para reservar el run_id, lanzamos en thread,
            # y devolvemos al cliente inmediatamente para que pueda hacer polling.
            try:
                orch = Orchestrator(Path(flow['flow_path']), context_overrides=overrides or None)
                # Persistimos sincrónicamente antes de lanzar el thread para
                # garantizar que el polling vea el run desde el primer tick.
                orch.state['status'] = 'running'
                orch._persist()
            except Exception as exc:  # noqa: BLE001
                return self._send_json({'ok': False, 'error': str(exc)}, status=500)
            run_id = orch.run_id
            flow_id = orch.definition.id

            def _runner() -> None:
                try:
                    orch.run()
                except FlowExecutionError:
                    pass  # El estado quedó persistido como failed.
                except Exception:  # noqa: BLE001
                    pass

            threading.Thread(target=_runner, daemon=True).start()
            return self._send_json({
                'ok': True,
                'run_id': run_id,
                'status': 'running',
                'flow_id': flow_id,
            })
        if path.startswith('/api/hook/'):
            folder = _safe_folder(path[len('/api/hook/'):].strip('/'))
            if folder is None:
                return self._send_json({'ok': False, 'error': 'folder inválido'}, status=400)
            if not self._check_webhook_token():
                return self._send_json(
                    {'ok': False, 'error': 'token inválido o AUTOMA_WEBHOOK_TOKEN no configurado'},
                    status=401,
                )
            flow = get_flow_by_folder(folder)
            if not flow:
                return self._send_json({'ok': False, 'error': 'flow no encontrado'}, status=404)
            if _is_preview(flow):
                return self._send_json({'ok': False, 'error': 'flow en preview — aún no operativo (ver docs/ROADMAP.md)'}, status=409)
            try:
                state = Orchestrator(Path(flow['flow_path'])).run()
                return self._send_json({
                    'ok': True,
                    'run_id': state['run_id'],
                    'status': state['status'],
                    'flow_id': state['flow_id'],
                })
            except FlowExecutionError as exc:
                return self._send_json({'ok': False, 'error': str(exc)}, status=500)
        if path == '/run':
            params = parse_qs(parsed.query)
            folder = _safe_folder(params.get('flow', [''])[0])
            if folder is None:
                return self._send_html(html_page('Error', '<div class="empty"><h4>Folder inválido</h4></div>'), status=400)
            flow = get_flow_by_folder(folder)
            if not flow:
                return self._send_html(html_page('Error', '<div class="empty"><h4>Flujo no encontrado</h4></div>'), status=404)
            if _is_preview(flow):
                return self._send_html(html_page('Preview', '<div class="card" style="background:var(--warning-soft);color:var(--warning)">🚧 Este flow está en preview y aún no es operativo. Ver <a href="https://github.com/vladimiracunadev-create/automa-pc/blob/main/docs/ROADMAP.md">docs/ROADMAP.md</a>.</div>'), status=409)
            try:
                state = Orchestrator(Path(flow['flow_path'])).run()
                return self._redirect(f"/run/{state['flow_id']}/{state['run_id']}")
            except FlowExecutionError as exc:
                return self._send_html(html_page('Ejecución con error', f'<div class="card" style="background:var(--danger-soft);color:var(--danger)">{html.escape(str(exc))}</div>'), status=500)
        if path.startswith('/flow/') and path.endswith('/config'):
            parts = [p for p in path.split('/') if p]
            folder = _safe_folder(parts[1] if len(parts) > 1 else '')
            if folder is None:
                return self._send_html(html_page('Error', '<div class="empty"><h4>Folder inválido</h4></div>'), status=400)
            form = self._read_form()
            try:
                config = json.loads(form.get('config_json', ['{}'])[0])
                set_flow_config(folder, config)
                return self._send_html(render_flow_config(folder, message='Configuración guardada correctamente.'))
            except Exception as exc:
                return self._send_html(render_flow_config(folder, message=f'Error al guardar: {exc}'), status=400)
        if path.startswith('/flow/') and path.endswith('/schedule'):
            parts = [p for p in path.split('/') if p]
            folder = _safe_folder(parts[1] if len(parts) > 1 else '')
            if folder is None:
                return self._send_html(html_page('Error', '<div class="empty"><h4>Folder inválido</h4></div>'), status=400)
            preview_flow = get_flow_by_folder(folder)
            if preview_flow and _is_preview(preview_flow):
                return self._send_html(html_page('Preview', '<div class="card" style="background:var(--warning-soft);color:var(--warning)">🚧 No se puede programar un flow en preview. Ver <a href="https://github.com/vladimiracunadev-create/automa-pc/blob/main/docs/ROADMAP.md">docs/ROADMAP.md</a>.</div>'), status=409)
            form = self._read_form()
            enabled = 'enabled' in form
            cron_expression = (form.get('cron_expression', [''])[0] or '').strip() or None
            interval_seconds = (
                int(form.get('interval_seconds', ['60'])[0])
                if enabled and not cron_expression
                else None
            )
            try:
                set_schedule(
                    folder,
                    enabled=enabled,
                    interval_seconds=interval_seconds,
                    cron_expression=cron_expression,
                )
                return self._redirect('/#schedule')
            except Exception as exc:
                return self._send_html(
                    render_flow_config(folder, message=f'Error en scheduler: {exc}'),
                    status=400,
                )
        return self._send_html(html_page('No encontrado', '<div class="empty"><h4>Ruta POST inexistente</h4></div>'), status=404)


def run_server(host: str = '127.0.0.1', port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f'Panel disponible en http://{host}:{port}')
    server.serve_forever()


if __name__ == '__main__':
    run_server()
