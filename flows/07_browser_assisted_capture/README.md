# 🌐 07 · Captura asistida por navegador

> Abre una página HTML local en el navegador, espera, captura pantalla y deja evidencia.

| | |
| --- | --- |
| **Familia** | navegador |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS (con sesión gráfica) |
| **Internet** | ❌ no requerido (página local) |
| **Modifica el sistema** | ⚠️ abre el navegador por defecto del usuario |

---

## 🎯 Para qué sirve

- 🌐 Validar que el navegador renderiza una página local de control.
- 📸 Documentar el estado de un dashboard interno sin internet.
- 🔄 Plantilla para flows que combinan apertura URL + evidencia visual.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `open_control_page` | `ui.open_file_in_browser` | Convierte `data/web/control_page.html` a `file://` URI y llama `webbrowser.open()`. |
| 2 | `wait_browser` | `system.wait_seconds` | Espera 2s. |
| 3 | `capture_screen` | `screen.capture_screenshot` | Captura pantalla completa con el navegador. |
| 4 | `analyze_capture` | `vision.analyze_image` (metadata) | Solo dimensiones/formato, sin OCR. |
| 5 | `write_report` | `filesystem.write_json` | Reporte. |

## ⚙️ Configuración

La página a abrir está en el manifest (`data/web/control_page.html`).

## 📋 Requisitos

- ✅ Sesión gráfica activa.
- ✅ Navegador por defecto configurado (Edge en Windows fresco).
- ✅ El archivo `data/web/control_page.html` existe en el repo.
- ❌ NO requiere internet.

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": [
    "ui.open_file_in_browser", "system.wait_seconds",
    "screen.capture_screenshot", "vision.analyze_image", "filesystem.write_json"
  ],
  "allowed_paths": ["data/web", "output/screenshots", "output/reports"],
  "max_runtime_seconds": 30
}
```

## ⚠️ Limitaciones

- ⚠️ **Abre una pestaña nueva en cada corrida**. Si lo programas, llenarás de pestañas.
- ❌ No cierra la pestaña al terminar.
- ❌ No espera evento DOM real, solo `wait_seconds`.
- ❌ No interactúa con el navegador (no click, no scroll).
- 💡 Para automatización web seria, usa Selenium/Playwright como acción externa via plugin.

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Página a abrir | `params.path` en paso 1 |
| Tiempo de espera | `params.seconds` en paso 2 |
| URL externa | Cambiar `ui.open_file_in_browser` por `ui.open_url` |

## 📤 Salidas

- 🖼️ `output/screenshots/browser_<ts>.png`
- 📊 `output/reports/browser_assisted_capture_<ts>.json`

## ⚡ Ejecución

```bash
flujo run flows/07_browser_assisted_capture
# NO recomendado para scheduler frecuente — abre pestañas
```
