# 🌐 12 · Captura del navegador (Playwright headless)

> Usa Playwright + Chromium headless para capturar SOLO el contenido renderizado de una URL o archivo HTML local. NO captura el escritorio.

| | |
| --- | --- |
| **Familia** | navegador |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS · ✅ funciona headless |
| **Internet** | ⚠️ requerido si la URL es externa |
| **Modifica el sistema** | ❌ solo escribe en `output/` |

---

## 🎯 Diferencia con el flow 01

| | Flow 01 — captura escritorio | Flow 12 — captura navegador |
| --- | --- | --- |
| Tecnología | `mss` o `Pillow.ImageGrab` | Playwright + Chromium headless |
| Captura | toda la pantalla del PC | solo el contenido del DOM renderizado |
| Tamaño | resolución del monitor (1920×1080 típico) | viewport configurable + página completa |
| Headless | ❌ requiere sesión gráfica | ✅ funciona sin display |
| Caso de uso | evidencia visual del PC | screenshot de páginas web/dashboards |

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `capture_browser_page` | `browser.capture_page` | Lanza Chromium headless, navega a la URL, espera `wait_seconds`, hace screenshot de toda la página y devuelve `image_path`, `title`, `width`, `height`, `size_bytes`. |

## ⚙️ Configuración

```json
{
  "target_url": "data/web/control_page.html",
  "full_page": true,
  "viewport_width": 1280,
  "viewport_height": 800,
  "wait_seconds": 1
}
```

| Clave | Tipo | Efecto |
| --- | --- | --- |
| `target_url` | string | URL `http://`/`https://` o ruta a HTML local |
| `full_page` | bool | True = página entera (incluye scroll); False = solo viewport |
| `viewport_width` / `viewport_height` | int | Tamaño de la ventana del navegador |
| `wait_seconds` | float | Espera adicional tras `load` para JS |

## 📋 Requisitos

- ✅ `playwright` Python lib: `pip install playwright`
- ✅ Chromium descargado: `python -m playwright install chromium`
- ❌ NO requiere sesión gráfica (headless real)
- ⚠️ Solo internet si la URL es externa

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["browser.capture_page"],
  "allowed_paths": ["data/web", "output/screenshots"],
  "max_runtime_seconds": 60
}
```

## ⚠️ Limitaciones

- ❌ La primera ejecución descarga Chromium (~150 MB) automáticamente.
- ❌ NO ejecuta clicks ni interacciones — solo captura.
- ⚠️ Sites con bot-detection (Cloudflare etc) pueden bloquear el headless.

## 🔓 Open Source

Repo upstream: <https://github.com/microsoft/playwright-python>

## 📤 Salidas

- 🖼️ `output/screenshots/browser_page_<ts>.png` — captura PNG real del DOM renderizado

## ⚡ Ejecución

```bash
flujo run flows/12_screen_capture_browser
```
