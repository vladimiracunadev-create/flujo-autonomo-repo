# 👁️ Inventario OCR del escritorio

## 🎯 Para qué sirve

Producir un **inventario estructurado de todo lo que es texto visible en la pantalla** en este momento: títulos de ventanas, contenido de apps abiertas, notificaciones, badges del system tray, hora del reloj, todo lo que `tesseract` pueda leer.

Es la primitiva que abre el camino a casos más ricos:

- **Auditoría visual**: ¿hay algún cartel de error visible? ¿qué apps están abiertas?
- **Verificación de estado**: "antes de hacer clic, confirma que el texto X está en pantalla".
- **Búsqueda por nombre**: encontrar la bbox de un botón por su label para clicarlo después con `ui.click_bbox`.

## 🧭 Flujo paso a paso

1. **capture_desktop** → `mss` captura la pantalla completa a PNG con timestamp.
2. **ocr_full_image** → pasa el PNG por `pytesseract` (vía el analyzer `ocr` de `actions.vision`); devuelve `{text, matches: [{text, bbox, confidence}, ...]}`.
3. **save_inventory** → guarda el resultado completo + metadata de la captura en JSON.

## ⚙️ Configuración

Este flow **no tiene parámetros** — siempre captura toda la pantalla. Para limitar a una región específica usar el caso futuro `19_taskbar_capture` o agregar `screen.capture_region` (ver [docs/ROADMAP.md](../../docs/ROADMAP.md) §Fase 2).

## 📋 Requisitos

- Sesión Windows interactiva con escritorio gráfico.
- `tesseract` instalado y accesible — el wrapper Python (`pytesseract`) ya viene como dependencia, pero el binario nativo se instala aparte:
  - **Windows**: <https://github.com/UB-Mannheim/tesseract/wiki> (instalador oficial).
  - Después del instalador, asegurar que `tesseract.exe` está en `PATH`.

Si tesseract no está, el OCR falla limpio con un mensaje claro y el step queda `failed`.

## 🛡️ Sandbox sugerido

```json
"allowed_actions": ["screen.capture_screenshot", "vision.ocr_image", "filesystem.write_json"],
"allowed_paths": ["output/screenshots", "output/reports"],
"max_runtime_seconds": 30
```

Aplicado en el manifest. El flow solo escribe en `output/`.

## ⚠️ Limitaciones honestas

- **Velocidad**: OCR de la pantalla completa (1920×1080) tarda ~2–5s en CPU típico. No correr en bucle apretado.
- **Precisión**: tesseract trabaja bien con texto limpio sobre fondo claro. Texto sobre imágenes complejas, gradientes, o tipografías pequeñas puede salir con errores. Para verificación binaria ("¿existe la palabra X?"), `vision.find_text_in_image` (que normaliza case y hace búsqueda parcial) es más robusto que comparar strings exactos.
- **Idioma**: el analyzer `ocr` usa el idioma por defecto de la instalación de tesseract. Para español/inglés mixtos puede haber que ajustar el modelo de tesseract instalado.
- **Multimonitor**: captura la pantalla principal; el inventario no incluye contenido de monitores secundarios.

## 🎮 Control que tienes

- Encadenable: este flow + un step `rules.evaluate` con `contains` para alertar si aparece una palabra (ej. "Error", "Sin conexión").
- Programable: capturar inventario cada N minutos para detectar cambios entre runs.
- Histórico del panel muestra el PNG en hero + el JSON con todos los matches en formato legible.

## 📤 Salidas

- **PNG**: `output/screenshots/desktop_ocr_<timestamp>.png` — captura cruda.
- **JSON**: `output/reports/desktop_ocr_inventory_<timestamp>.json` — estructura:

```json
{
  "screenshot": {
    "image_path": "output/screenshots/desktop_ocr_20260602_120000.png",
    "width": 1920,
    "height": 1080,
    "method": "mss"
  },
  "ocr": {
    "image_path": "output/screenshots/desktop_ocr_20260602_120000.png",
    "analyzer": "ocr",
    "text": "todo el texto concatenado…",
    "matches": [
      {"text": "Mi documento.txt", "bbox": {"left": 240, "top": 80, "width": 120, "height": 16}, "confidence": 93}
    ]
  }
}
```

## ⚡ Ejecución

Desde el panel: **Ejecutar** → `Alt+=` o click en la card.

CLI:

```bash
flujo run flows/12_desktop_ocr_inventory
```
