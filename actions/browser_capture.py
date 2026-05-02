"""Captura de páginas web/HTML con Playwright headless.

A diferencia de ``screen.capture_screenshot`` (que captura todo el escritorio
con mss/Pillow), esta acción usa **Playwright** + Chromium headless para tomar
screenshot SOLO del contenido renderizado de una URL o archivo HTML local.

Es la diferencia entre "una foto de mi escritorio Windows" (caso 1) y "una
foto del DOM renderizado de una página" (caso 12).

Repo upstream: https://github.com/microsoft/playwright-python
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _to_url(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme in ('http', 'https', 'file'):
        return target
    candidate = Path(target).resolve()
    if not candidate.exists():
        raise FileNotFoundError(
            f'Página no encontrada y no es URL válida: {target}'
        )
    return candidate.as_uri()


def capture_page(
    target: str,
    output_path: str,
    full_page: bool = True,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    wait_seconds: float = 1.0,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Captura una página renderizada como PNG.

    Args:
        target: URL (``http://...``, ``file://...``) o ruta local a un .html.
        output_path: dónde escribir el PNG.
        full_page: True captura toda la página (incluye lo que está fuera del
            viewport por scroll); False captura sólo el viewport.
        viewport_width / viewport_height: tamaño de la ventana del navegador.
        wait_seconds: espera adicional tras `load` para dar tiempo a JS.
        timeout_seconds: timeout global del navegador.

    Returns:
        dict con ``image_path``, ``url``, ``width``, ``height``,
        ``full_page``, ``method`` (siempre "playwright").
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'playwright no está instalado. Ejecuta: '
            'pip install playwright && python -m playwright install chromium'
        ) from exc

    url = _to_url(target)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={'width': int(viewport_width), 'height': int(viewport_height)}
            )
            page = context.new_page()
            page.set_default_timeout(int(timeout_seconds * 1000))
            page.goto(url, wait_until='load')
            if wait_seconds > 0:
                page.wait_for_timeout(int(wait_seconds * 1000))
            page.screenshot(path=str(out), full_page=bool(full_page))
            title = page.title()
        finally:
            browser.close()

    size = out.stat().st_size
    return {
        'image_path': str(out),
        'url': url,
        'title': title,
        'width': int(viewport_width),
        'height': int(viewport_height),
        'full_page': bool(full_page),
        'size_bytes': size,
        'method': 'playwright',
    }
