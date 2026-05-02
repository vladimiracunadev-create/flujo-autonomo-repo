"""Acción ``browser.fill_form``: abre URL/HTML, rellena formulario y devuelve datos.

Operación avanzada del sistema: lanza Chromium (visible o headless),
genera 10 datos random, llena cada campo del DOM uno por uno con
``slow_mo`` para que sea visualmente observable, dispara submit, espera
la validación JS de la página y devuelve el resultado.

NO genera capturas PNG: el output es **solo datos** (los 10 campos
enviados, el texto de validación, si se mostró el JSON server-side, etc).
Si ``save_data_path`` se especifica, persiste también un JSON con los
datos generados y el resultado.

Repos open-source usados:
- https://github.com/microsoft/playwright-python
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_NOMBRES = ['Juan', 'María', 'Carlos', 'Ana', 'Pedro', 'Lucía', 'Javier', 'Camila',
            'Diego', 'Valentina', 'Tomás', 'Sofía', 'Andrés', 'Isabel', 'Felipe']
_APELLIDOS = ['Pérez', 'González', 'Rodríguez', 'López', 'Martínez', 'Sánchez',
              'García', 'Fernández', 'Torres', 'Ramírez', 'Flores', 'Castro']
_PROFESIONES = ['Ingeniero', 'Diseñadora', 'Profesor', 'Médica', 'Abogado',
                'Periodista', 'Arquitecta', 'Programador', 'Contadora', 'Chef']
_CIUDADES = {
    'CL': ['Santiago', 'Valparaíso', 'Concepción', 'Antofagasta'],
    'AR': ['Buenos Aires', 'Córdoba', 'Mendoza', 'Rosario'],
    'MX': ['Ciudad de México', 'Guadalajara', 'Monterrey', 'Puebla'],
    'ES': ['Madrid', 'Barcelona', 'Sevilla', 'Valencia'],
    'CO': ['Bogotá', 'Medellín', 'Cali', 'Cartagena'],
    'PE': ['Lima', 'Arequipa', 'Trujillo', 'Cusco'],
}
_CALLES = ['Av. Libertad', 'Calle Mayor', 'Av. Las Condes', 'Av. Providencia',
           'Calle 9 de Julio', 'Av. Reforma', 'Calle Real', 'Pasaje del Sol']
_DOMINIOS = ['mail.com', 'demo.io', 'example.org', 'workspace.dev', 'inbox.cl']
_COMENTARIOS = [
    'Este registro fue generado automáticamente por el flow para demostrar el llenado.',
    'Datos sintéticos creados por el sistema con fines de prueba operativa.',
    'Formulario completado desde una corrida automatizada en headless Chromium.',
    'Probando el flujo completo: apertura, llenado, validación y guardado.',
    'Test de integración E2E: 10 campos rellenados con valores random.',
]


def _random_phone() -> str:
    return '+56 9 ' + ''.join(str(random.randint(0, 9)) for _ in range(8))


def _random_birth_date() -> str:
    today = date.today()
    days_back = random.randint(365 * 18, 365 * 65)
    d = today - timedelta(days=days_back)
    return d.isoformat()


def _generate_random_data() -> dict[str, str]:
    nombre = random.choice(_NOMBRES)
    apellido = random.choice(_APELLIDOS)
    pais = random.choice(list(_CIUDADES.keys()))
    ciudad = random.choice(_CIUDADES[pais])
    email_user = f'{nombre.lower()}.{apellido.lower()}{random.randint(10, 99)}'
    return {
        'nombre': nombre,
        'apellido': apellido,
        'email': f'{email_user}@{random.choice(_DOMINIOS)}',
        'telefono': _random_phone(),
        'direccion': f'{random.choice(_CALLES)} {random.randint(100, 9999)}',
        'ciudad': ciudad,
        'pais': pais,
        'fecha_nacimiento': _random_birth_date(),
        'profesion': random.choice(_PROFESIONES),
        'comentario': random.choice(_COMENTARIOS),
    }


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
    headless: bool = False,
    slow_mo_ms: int = 250,
    save_data_path: str | None = None,
    viewport_width: int = 1280,
    viewport_height: int = 900,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Abre la página, rellena el form y devuelve los datos enviados + validación.

    NO genera PNG. Solo datos.

    Si ``headless=False`` (default) **lanzas una ventana real de Chromium**
    visible en pantalla. ``slow_mo_ms`` espera N ms entre cada acción para
    que veas cómo se llenan los campos. Para CI/headless usa headless=True.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'playwright no está instalado. Ejecuta: '
            'pip install playwright && python -m playwright install chromium'
        ) from exc

    url = _to_url(target)
    data = _generate_random_data()
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
                page.fill(f'#{field}', data[field])
            page.select_option('#pais', data['pais'])

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

    is_success = validation_text.lower().startswith('✅') or 'válido' in validation_text.lower()

    saved_to: str | None = None
    if save_data_path:
        target_save = Path(save_data_path)
        target_save.parent.mkdir(parents=True, exist_ok=True)
        target_save.write_text(
            json.dumps({
                'url': url,
                'data_sent': data,
                'validation_text': validation_text,
                'is_success': is_success,
                'submitted_visible': submitted_visible,
                'submitted_payload': submitted_payload_text,
            }, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        saved_to = str(target_save)

    return {
        'url': url,
        'fields_filled': len(data),
        'data_sent': data,
        'validation_text': validation_text,
        'is_success': is_success,
        'submitted_visible': submitted_visible,
        'submitted_payload': submitted_payload_text,
        'saved_to': saved_to,
        'method': 'playwright',
        'headless': bool(headless),
    }
