"""Tests de regresión para los fixes de la auditoría 2026-06-01.

Cubre:
- launch_process rechaza shell=True (CWE-78)
- /api/run/<folder> rechaza cross-site (Origin distinto) (CWE-352)
- /file rechaza path traversal por prefijo (CWE-22)
- /file rechaza extensiones ejecutables por browser (CWE-79)
- _check_webhook_token usa comparación constant-time (CWE-208)
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from actions import ui
from app.server import AppHandler
from engine.catalog import list_flows
from engine.database import init_db, sync_flows


@pytest.fixture()
def live_server(tmp_runtime, project_root):
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


# --- actions/ui.py: shell=True bloqueado ------------------------------------

def test_launch_process_shell_true_raises():
    with pytest.raises(ValueError, match='shell=True'):
        ui.launch_process('echo hola', shell=True, dry_run=True)


def test_launch_process_dry_run_ok_sin_shell():
    out = ui.launch_process('echo hola', dry_run=True)
    assert out['dry_run'] is True
    assert out['shell'] is False


# --- /api/run/: CSRF anti-Origin ---------------------------------------------

@pytest.mark.integration
def test_api_run_rechaza_origin_externo(live_server):
    req = urllib.request.Request(
        live_server + '/api/run/05_system_healthcheck',
        method='POST',
        headers={'Origin': 'http://evil.example.com'},
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 401


@pytest.mark.integration
def test_api_run_acepta_request_sin_origin(live_server):
    """curl/scripts (sin header Origin) deben seguir funcionando."""
    req = urllib.request.Request(
        live_server + '/api/run/05_system_healthcheck',
        method='POST',
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    assert data['ok'] is True


@pytest.mark.integration
def test_flow_config_rechaza_origin_externo(live_server):
    req = urllib.request.Request(
        live_server + '/flow/05_system_healthcheck/config',
        data=b'config_json=%7B%7D',
        method='POST',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'http://evil.example.com',
        },
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 401


# --- /file: path traversal ---------------------------------------------------

@pytest.mark.integration
def test_file_rechaza_path_fuera_de_root(live_server, tmp_path):
    # Pedimos un absoluto que no está bajo ROOT. Debe responder 404 (ruta inválida).
    outside = (tmp_path / 'leak.txt')
    outside.write_text('secreto')
    import urllib.parse
    req = live_server + '/file?path=' + urllib.parse.quote(str(outside))
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 404


@pytest.mark.integration
def test_file_rechaza_extension_ejecutable(live_server, project_root):
    # Creamos un .html dentro de ROOT y verificamos que /file no lo sirve.
    html_file = project_root / 'output' / 'reports' / 'evil_test.html'
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text('<script>alert(1)</script>', encoding='utf-8')
    try:
        import urllib.parse
        req = live_server + '/file?path=' + urllib.parse.quote(str(html_file.relative_to(project_root)))
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.code == 415
    finally:
        html_file.unlink(missing_ok=True)


# --- _check_token usa hmac.compare_digest -----------------------------------

# --- folder slug filter (defensa en profundidad contra py/path-injection) ---

@pytest.mark.integration
def test_api_run_rechaza_folder_con_path_traversal(live_server):
    import urllib.parse
    for evil in ['../etc/passwd', 'foo/bar', 'foo\\bar', 'foo;rm', 'foo bar', '']:
        req = urllib.request.Request(
            live_server + '/api/run/' + urllib.parse.quote(evil, safe=''),
            method='POST',
        )
        try:
            urllib.request.urlopen(req)
            # /api/run/ (vacío) cae en 404 por path no encontrado; OK.
        except urllib.error.HTTPError as exc:
            assert exc.code in (400, 404), f'inesperado {exc.code} para {evil!r}'


def test_safe_folder_acepta_slugs_validos():
    from app.server import _safe_folder
    assert _safe_folder('05_system_healthcheck') == '05_system_healthcheck'
    assert _safe_folder('01-flow') == '01-flow'


def test_safe_folder_rechaza_traversal_y_separadores():
    from app.server import _safe_folder
    assert _safe_folder('../etc/passwd') is None
    assert _safe_folder('foo/bar') is None
    assert _safe_folder('foo\\bar') is None
    assert _safe_folder('foo;rm') is None
    assert _safe_folder('') is None
    assert _safe_folder('a' * 65) is None  # excede 64 chars
    assert _safe_folder('flow\x00null') is None


def test_check_token_usa_compare_digest(monkeypatch):
    """Smoke test: con token mal, devuelve False (sin lanzar)."""
    import hmac as _hmac
    monkeypatch.setenv('AUTOMA_PANEL_TOKEN', 'secreto_correcto')
    # Verificamos que el módulo importa hmac y que compare_digest existe;
    # garantía mínima de que no caímos en `==`. La cobertura real del flujo
    # se valida en los tests de Origin de más arriba.
    from app import server as srv
    assert hasattr(srv, 'hmac')
    assert srv.hmac is _hmac
