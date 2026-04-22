from __future__ import annotations

import html
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from engine.catalog import (
    find_run,
    get_flow_by_folder,
    list_flows,
    list_runs,
    load_run_events,
    load_run_steps,
)
from engine.paths import root_dir
from engine.database import get_flow_config, get_schedule, init_db, set_flow_config, set_schedule, sync_flows
from engine.orchestrator import FlowExecutionError, Orchestrator
from engine.scheduler import SchedulerService

ROOT = root_dir()
SCHEDULER = SchedulerService(loop_sleep_seconds=2.0)
SCHEDULER.start_in_background()
init_db()
sync_flows(list_flows())


def html_page(title: str, body: str) -> bytes:
    page = f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin:0; background:#f4f7fb; color:#1f2937; }}
header {{ background:#0f172a; color:white; padding:20px 24px; }}
main {{ padding:24px; max-width:1340px; margin:0 auto; }}
a {{ color:#1d4ed8; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:16px; }}
.card {{ background:white; border-radius:18px; padding:18px; box-shadow:0 10px 26px rgba(0,0,0,.06); }}
.buttons {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }}
button, .button {{ border:none; border-radius:10px; padding:10px 14px; background:#111827; color:white; cursor:pointer; text-decoration:none; display:inline-block; }}
.button.secondary {{ background:#e5e7eb; color:#111827; }}
.button.success {{ background:#14532d; }}
.button.warn {{ background:#9a3412; }}
.badge {{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; margin-right:6px; background:#e5e7eb; }}
.ok {{ background:#dcfce7; color:#166534; }}
.failed {{ background:#fee2e2; color:#991b1b; }}
.running {{ background:#dbeafe; color:#1d4ed8; }}
pre {{ background:#0f172a; color:#e2e8f0; padding:14px; border-radius:14px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; background:white; border-radius:14px; overflow:hidden; }}
th, td {{ padding:12px; border-bottom:1px solid #e5e7eb; text-align:left; vertical-align:top; }}
textarea {{ width:100%; min-height:280px; font-family: ui-monospace, monospace; border-radius:12px; border:1px solid #cbd5e1; padding:12px; }}
input[type='number'] {{ width:140px; padding:8px; border:1px solid #cbd5e1; border-radius:10px; }}
label {{ display:block; margin-bottom:8px; font-weight:600; }}
.two-col {{ display:grid; grid-template-columns:1.1fr .9fr; gap:18px; }}
.muted {{ color:#6b7280; }}
.path {{ font-family:ui-monospace,monospace; font-size:13px; }}
@media (max-width:960px) {{ .two-col {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header><div><a href="/" style="color:white">Inicio</a></div><h1 style="margin:10px 0 0 0">{html.escape(title)}</h1></header>
<main>{body}</main>
</body>
</html>'''
    return page.encode('utf-8')


def badge(status: str) -> str:
    cls = 'ok' if status == 'completed' else 'failed' if status == 'failed' else 'running'
    return f'<span class="badge {cls}">{html.escape(status)}</span>'


def safe_json_loads(text: str | None):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def render_home() -> bytes:
    flows = list_flows()
    runs = list_runs(limit=200)
    runs_by_flow = {}
    for run in runs:
        runs_by_flow.setdefault(run['flow_id'], []).append(run)
    cards = []
    for flow in flows:
        history = runs_by_flow.get(flow['id'], [])
        latest = history[0] if history else None
        schedule = get_schedule(flow['folder'])
        cards.append(
            f'''
            <div class="card">
              <div><span class="badge">{html.escape(flow.get('family','general'))}</span></div>
              <h2 style="margin:8px 0 6px 0">{html.escape(flow['name'])}</h2>
              <div class="muted">{html.escape(flow['description'])}</div>
              <div style="margin-top:12px"><strong>Flujo:</strong> <span class="path">{html.escape(flow['folder'])}</span></div>
              <div><strong>Pasos:</strong> {len(flow.get('steps', []))}</div>
              <div><strong>Scheduler:</strong> {'activo cada ' + str(schedule.get('interval_seconds')) + 's' if int(schedule.get('enabled') or 0) else 'desactivado'}</div>
              <div><strong>Última corrida:</strong> {badge(latest['status']) if latest else '<span class="muted">sin ejecuciones</span>'}</div>
              <div class="buttons">
                <form method="post" action="/run?flow={flow['folder']}" style="display:inline"><button type="submit">Ejecutar proceso</button></form>
                <a class="button secondary" href="/flow/{flow['folder']}">Información</a>
                <a class="button secondary" href="/flow/{flow['folder']}/config">Configurar</a>
                <a class="button secondary" href="/flow/{flow['folder']}/history">Histórico</a>
              </div>
            </div>
            '''
        )
    body = f'''
    <div class="card" style="margin-bottom:18px">
      <p><strong>Primera versión operativa:</strong> índice principal + ejecución real + histórico SQLite + scheduler + configuración por flujo + branching condicional + OCR, visión y modo híbrido.</p>
      <p class="muted">Cada caso puede ejecutarse manualmente o quedar programado. El detalle de cada corrida guarda acciones, datos obtenidos, eventos y archivos generados.</p>
    </div>
    <div class="grid">{''.join(cards)}</div>
    '''
    return html_page('Centro de procesos autónomos', body)


def render_flow_info(folder: str) -> bytes:
    flow = get_flow_by_folder(folder)
    if not flow:
        return html_page('No encontrado', '<p>Flujo inexistente.</p>')
    readme = Path(flow['readme_path']).read_text(encoding='utf-8') if Path(flow['readme_path']).exists() else ''
    manifest = Path(flow['flow_path']) / 'manifest.json'
    manifest_text = manifest.read_text(encoding='utf-8')
    recent = list_runs(flow['id'], limit=10)
    rows = ''.join(
        f"<tr><td><a href='/run/{flow['id']}/{run['run_id']}'>{html.escape(run['run_id'])}</a></td><td>{badge(run['status'])}</td><td>{html.escape(str(run.get('created_at') or ''))}</td></tr>"
        for run in recent
    ) or '<tr><td colspan="3">Sin corridas</td></tr>'
    body = f'''
    <div class="two-col">
      <div>
        <div class="card">
          <div><span class="badge">{html.escape(flow.get('family','general'))}</span></div>
          <h2>{html.escape(flow['name'])}</h2>
          <p>{html.escape(flow['description'])}</p>
          <div class="buttons">
            <form method="post" action="/run?flow={flow['folder']}" style="display:inline"><button type="submit">Ejecutar ahora</button></form>
            <a class="button secondary" href="/flow/{flow['folder']}/config">Editar configuración</a>
            <a class="button secondary" href="/flow/{flow['folder']}/history">Ver histórico</a>
          </div>
        </div>
        <div class="card" style="margin-top:16px">
          <h3>README del caso</h3>
          <pre>{html.escape(readme)}</pre>
        </div>
      </div>
      <div>
        <div class="card">
          <h3>Manifest</h3>
          <pre>{html.escape(manifest_text)}</pre>
        </div>
        <div class="card" style="margin-top:16px">
          <h3>Últimas corridas</h3>
          <table><thead><tr><th>Run</th><th>Estado</th><th>Fecha</th></tr></thead><tbody>{rows}</tbody></table>
        </div>
      </div>
    </div>
    '''
    return html_page(f'Información: {flow["name"]}', body)


def render_flow_config(folder: str, message: str = '') -> bytes:
    flow = get_flow_by_folder(folder)
    if not flow:
        return html_page('No encontrado', '<p>Flujo inexistente.</p>')
    current = get_flow_config(folder)
    if current is None:
        current_path = Path(flow['context_example_path'])
        current = json.loads(current_path.read_text(encoding='utf-8')) if current_path.exists() else {}
    schedule = get_schedule(folder)
    body = f'''
    <div class="two-col">
      <div class="card">
        <h2>Configuración del flujo</h2>
        <p class="muted">Lo que guardes aquí será el contexto operativo por defecto del caso.</p>
        {f'<p><strong>{html.escape(message)}</strong></p>' if message else ''}
        <form method="post" action="/flow/{folder}/config">
          <label>JSON del contexto</label>
          <textarea name="config_json">{html.escape(json.dumps(current, ensure_ascii=False, indent=2))}</textarea>
          <div class="buttons"><button type="submit">Guardar configuración</button></div>
        </form>
      </div>
      <div class="card">
        <h2>Scheduler</h2>
        <form method="post" action="/flow/{folder}/schedule">
          <label><input type="checkbox" name="enabled" {'checked' if int(schedule.get('enabled') or 0) else ''}/> Activar scheduler</label>
          <label>Intervalo en segundos</label>
          <input type="number" min="1" name="interval_seconds" value="{html.escape(str(schedule.get('interval_seconds') or 60))}" />
          <div class="buttons"><button type="submit">Guardar scheduler</button></div>
        </form>
        <p><strong>Última ejecución programada:</strong> {html.escape(str(schedule.get('last_run_at') or 'n/a'))}</p>
        <p><strong>Próxima ejecución:</strong> {html.escape(str(schedule.get('next_run_at') or 'n/a'))}</p>
      </div>
    </div>
    '''
    return html_page(f'Configurar: {flow["name"]}', body)


def render_flow_history(folder: str) -> bytes:
    flow = get_flow_by_folder(folder)
    if not flow:
        return html_page('No encontrado', '<p>Flujo inexistente.</p>')
    runs = list_runs(flow['id'], limit=100)
    rows = ''.join(
        f"<tr><td><a href='/run/{flow['id']}/{run['run_id']}'>{html.escape(run['run_id'])}</a></td><td>{badge(run['status'])}</td><td>{html.escape(str(run.get('created_at') or ''))}</td><td>{html.escape(str(run.get('duration_seconds') or ''))}</td></tr>"
        for run in runs
    ) or '<tr><td colspan="4">Sin corridas</td></tr>'
    body = f'''
    <div class="card">
      <h2>Histórico: {html.escape(flow['name'])}</h2>
      <table><thead><tr><th>Run</th><th>Estado</th><th>Creado</th><th>Duración (s)</th></tr></thead><tbody>{rows}</tbody></table>
    </div>
    '''
    return html_page(f'Histórico: {flow["name"]}', body)


def render_run_detail(flow_id: str, run_id: str) -> bytes:
    run = find_run(flow_id, run_id)
    if not run:
        return html_page('No encontrado', '<p>Corrida inexistente.</p>')
    steps = load_run_steps(flow_id, run_id)
    events = load_run_events(flow_id, run_id)
    context = safe_json_loads(run.get('context_json')) or {}
    outputs = safe_json_loads(run.get('outputs_json')) or []
    error = safe_json_loads(run.get('error_json'))
    step_rows = ''.join(
        f"<tr><td>{index}</td><td>{html.escape(step['step_id'])}</td><td>{html.escape(step['action'])}</td><td>{badge(step['status'])}</td><td>{html.escape(str(step['attempt']))}</td><td><pre>{html.escape(str(safe_json_loads(step.get('result_json')) or step.get('error_text') or ''))}</pre></td></tr>"
        for index, step in enumerate(steps, start=1)
    ) or '<tr><td colspan="6">Sin pasos</td></tr>'
    output_items = ''.join(
        f"<li><a href='/file?path={html.escape(item.get('path', ''))}'>{html.escape(item.get('name', item.get('path', 'archivo')))}</a> <span class='muted path'>{html.escape(item.get('path', ''))}</span></li>"
        for item in outputs if isinstance(item, dict) and item.get('path')
    ) or '<li>No se detectaron salidas físicas.</li>'
    event_lines = []
    for event in events:
        payload = safe_json_loads(event.get('payload_json'))
        event_lines.append({'event_time': event.get('event_time'), 'event_type': event.get('event_type'), 'payload': payload})
    body = f'''
    <div class="card">
      <div>{badge(run['status'])}</div>
      <h2>Detalle de corrida</h2>
      <p><strong>Flujo:</strong> {html.escape(run['flow_name'])} <span class="path">({html.escape(run['flow_id'])})</span></p>
      <p><strong>Run ID:</strong> <span class="path">{html.escape(run['run_id'])}</span></p>
      <p><strong>Duración:</strong> {html.escape(str(run.get('duration_seconds') or 'n/a'))} s</p>
      <p><strong>Error final:</strong> {html.escape(json.dumps(error, ensure_ascii=False) if error else 'sin error')}</p>
    </div>
    <div class="two-col">
      <div>
        <div class="card">
          <h3>Acciones ejecutadas</h3>
          <table><thead><tr><th>#</th><th>Paso</th><th>Acción</th><th>Estado</th><th>Intento</th><th>Resultado</th></tr></thead><tbody>{step_rows}</tbody></table>
        </div>
        <div class="card" style="margin-top:16px">
          <h3>Eventos técnicos</h3>
          <pre>{html.escape(json.dumps(event_lines, ensure_ascii=False, indent=2))}</pre>
        </div>
      </div>
      <div>
        <div class="card">
          <h3>Datos finales obtenidos</h3>
          <pre>{html.escape(json.dumps(context, ensure_ascii=False, indent=2))}</pre>
        </div>
        <div class="card" style="margin-top:16px">
          <h3>Salidas / despliegues / archivos</h3>
          <ul>{output_items}</ul>
        </div>
      </div>
    </div>
    '''
    return html_page(f'Detalle run: {run_id}', body)


class AppHandler(BaseHTTPRequestHandler):
    def _send_html(self, content: bytes, status: int = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', location)
        self.end_headers()

    def _read_form(self):
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length).decode('utf-8') if length else ''
        return parse_qs(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/':
            return self._send_html(render_home())
        if path.startswith('/flow/'):
            parts = [p for p in path.split('/') if p]
            folder = parts[1] if len(parts) > 1 else ''
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
            target = (ROOT / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
            if not str(target).startswith(str(ROOT.resolve())) or not target.exists() or not target.is_file():
                return self._send_html(html_page('Archivo no encontrado', '<p>Ruta inválida.</p>'), status=404)
            mime, _ = mimetypes.guess_type(str(target))
            content = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', mime or 'application/octet-stream')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        return self._send_html(html_page('No encontrado', '<p>Ruta inexistente.</p>'), status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/run':
            params = parse_qs(parsed.query)
            folder = params.get('flow', [''])[0]
            flow = get_flow_by_folder(folder)
            if not flow:
                return self._send_html(html_page('Error', '<p>Flujo no encontrado.</p>'), status=404)
            try:
                orchestrator = Orchestrator(Path(flow['flow_path']))
                state = orchestrator.run()
                return self._redirect(f"/run/{state['flow_id']}/{state['run_id']}")
            except FlowExecutionError as exc:
                return self._send_html(html_page('Ejecución con error', f'<p>{html.escape(str(exc))}</p>'), status=500)
        if path.startswith('/flow/') and path.endswith('/config'):
            parts = [p for p in path.split('/') if p]
            folder = parts[1]
            form = self._read_form()
            try:
                config = json.loads(form.get('config_json', ['{}'])[0])
                set_flow_config(folder, config)
                return self._send_html(render_flow_config(folder, message='Configuración guardada correctamente.'))
            except Exception as exc:
                return self._send_html(render_flow_config(folder, message=f'Error al guardar: {exc}'), status=400)
        if path.startswith('/flow/') and path.endswith('/schedule'):
            parts = [p for p in path.split('/') if p]
            folder = parts[1]
            form = self._read_form()
            enabled = 'enabled' in form
            interval_seconds = int(form.get('interval_seconds', ['60'])[0]) if enabled else None
            set_schedule(folder, enabled=enabled, interval_seconds=interval_seconds)
            return self._send_html(render_flow_config(folder, message='Scheduler actualizado.'))
        return self._send_html(html_page('No encontrado', '<p>Ruta POST inexistente.</p>'), status=404)


def run_server(host: str = '127.0.0.1', port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f'Panel disponible en http://{host}:{port}')
    server.serve_forever()


if __name__ == '__main__':
    run_server()
