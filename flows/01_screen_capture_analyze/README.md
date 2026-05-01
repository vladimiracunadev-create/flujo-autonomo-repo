# 📷 01 · Captura y análisis local de pantalla

> Toma una captura de la pantalla principal, ejecuta un analizador local sobre la imagen y deja un reporte JSON.

| | |
| --- | --- |
| **Familia** | pantalla |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS (con sesión gráfica) |
| **Internet** | ❌ no requerido |
| **Modifica el sistema** | ❌ solo escribe en `output/` |

---

## 🎯 Para qué sirve

- 📌 Validar que una aplicación esté abierta o que la pantalla muestre un estado esperado.
- 🗂️ Dejar evidencia visual periódica de un equipo (auditoría local).
- 🧪 Probar que la captura de pantalla funciona en este equipo antes de pasar a flows más complejos (10, 11).
- 🏗️ Servir como plantilla para flows con OCR, visión multimodal o reglas sobre la imagen.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace exactamente |
| --- | --- | --- | --- |
| 1 | `capture_screen` | `screen.capture_screenshot` | Captura el monitor primario con `mss` (fallback a `Pillow.ImageGrab` si `mss` falla). Guarda PNG en `output/screenshots/screen_<timestamp>.png`. Reintenta 1 vez si falla. |
| 2 | `analyze_capture` | `vision.analyze_image` | Pasa la imagen al analizador configurado (`mock`, `metadata` u `ocr`). Devuelve un dict con texto extraído / metadata / heurística. |
| 3 | `write_report` | `filesystem.write_json` | Persiste un JSON con `capture` (path, dimensiones, método) y `analysis` (resultado del analizador). |

## ⚙️ Configuración

`context.example.json`:

```json
{ "analyzer_override": "mock" }
```

| Clave | Valores | Efecto |
| --- | --- | --- |
| `analyzer_override` | `mock` · `metadata` · `ocr` | `mock` = heurística sin deps. `metadata` = solo Pillow. `ocr` = requiere Tesseract. |

## 📋 Requisitos

- ✅ Python 3.10+, `Pillow`, `mss`.
- ✅ **Sesión gráfica activa** (no funciona en SSH headless ni Windows lock screen).
- ⚠️ Si usas `analyzer_override = "ocr"`: **Tesseract OCR** instalado (`choco install tesseract` en Windows).

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["screen.capture_screenshot", "vision.analyze_image", "filesystem.write_json"],
  "allowed_paths": ["output/screenshots", "output/reports"],
  "max_runtime_seconds": 30
}
```

## ⚠️ Limitaciones

- ❌ No funciona si la pantalla está bloqueada o sin sesión interactiva.
- ❌ Solo captura el monitor primario (`monitors[1]`).
- ❌ El analizador `mock` no entiende contenido real — solo heurística básica.
- ⚠️ La captura puede contener información sensible. `output/` está en `.gitignore`.

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Ruta de salida del PNG | `params.output_path` en el manifest |
| Analizador | `analyzer_override` en `configs/01_screen_capture_analyze.json` |
| Reintentos | `retries` del paso `capture_screen` (actualmente 1) |
| Frecuencia | Activar scheduler desde el panel |

## 📤 Salidas

- 🖼️ `output/screenshots/screen_<ts>.png`
- 📊 `output/reports/screen_capture_analyze_<ts>.json`
- 💾 `db/runs.db` · 📜 `logs/*.jsonl` · 📂 `state/*.json`

## ⚡ Ejecución

```bash
flujo run flows/01_screen_capture_analyze
# Panel: tab "▶ Ejecutar" → click en la card
```
