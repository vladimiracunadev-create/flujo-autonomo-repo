"""Tests del handler HTTP del panel."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from app.server import AppHandler
from engine.catalog import list_flows
from engine.database import init_db, sync_flows


@pytest.fixture()
def live_server(tmp_runtime, project_root):
    # El handler del panel usa rutas relativas al cwd; tmp_runtime ya cambió la cwd.
    # Pero los flows reales viven en el repo, así que el catálogo apunta a project_root.
    import os
    os.chdir(project_root)
    init_db()
    sync_flows(list_flows())
    server = ThreadingHTTPServer(('127.0.0.1', 0), AppHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        time.sleep(0.05)
        yield f'http://127.0.0.1:{port}'
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.integration
def test_home_returns_three_tabs(live_server):
    with urllib.request.urlopen(live_server + '/') as resp:
        text = resp.read().decode('utf-8')
    assert 'data-tab="run"' in text
    assert 'data-tab="schedule"' in text
    assert 'data-tab="history"' in text
    assert 'Ejecutar' in text
    assert 'Programadas' in text
    assert 'Histórico' in text


@pytest.mark.integration
def test_healthz(live_server):
    with urllib.request.urlopen(live_server + '/healthz') as resp:
        data = json.loads(resp.read())
    assert data['status'] == 'ok'


@pytest.mark.integration
def test_api_flows_lists_known_folders(live_server):
    with urllib.request.urlopen(live_server + '/api/flows') as resp:
        data = json.loads(resp.read())
    folders = {item['folder'] for item in data}
    assert '05_system_healthcheck' in folders


@pytest.mark.integration
def test_api_run_endpoint_returns_run_id(live_server):
    """POST /api/run/<folder> ahora es asíncrono: devuelve run_id de inmediato."""
    req = urllib.request.Request(
        live_server + '/api/run/05_system_healthcheck',
        method='POST',
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    assert data['ok'] is True
    assert data['status'] == 'running'
    assert data['run_id']
    assert data['flow_id'] == 'system_healthcheck'


@pytest.mark.integration
def test_api_run_status_polling_lifecycle(live_server):
    """El endpoint de status debe pasar de running a completed para un flow rápido."""
    req = urllib.request.Request(
        live_server + '/api/run/05_system_healthcheck',
        method='POST',
    )
    with urllib.request.urlopen(req) as resp:
        run_data = json.loads(resp.read())
    run_id = run_data['run_id']

    final = None
    for _ in range(30):
        with urllib.request.urlopen(live_server + f'/api/runs/{run_id}/status') as resp:
            payload = json.loads(resp.read())
        assert payload['ok'] is True
        assert isinstance(payload['steps'], list)
        if payload['status'] in ('completed', 'failed'):
            final = payload
            break
        time.sleep(0.3)
    assert final is not None, 'el flow no terminó en el tiempo esperado'
    assert final['status'] == 'completed'
    statuses = {s['status'] for s in final['steps']}
    assert 'success' in statuses


@pytest.mark.integration
def test_api_run_unknown_folder_returns_404(live_server):
    req = urllib.request.Request(
        live_server + '/api/run/no_existe',
        method='POST',
    )
    try:
        urllib.request.urlopen(req)
        pytest.fail('Debería haber fallado con 404')
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
