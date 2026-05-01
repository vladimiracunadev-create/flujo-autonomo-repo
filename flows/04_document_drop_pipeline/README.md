# 📄 04 · Pipeline documental de entrada

> Escanea un buzón documental, clasifica archivos y resume contenido textual.

| | |
| --- | --- |
| **Familia** | documentos |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS · 🟢 headless |
| **Internet** | ❌ no requerido |
| **Modifica el sistema** | ❌ solo lee y escribe en `output/` |

---

## 🎯 Para qué sirve

- 📥 Procesar carpeta donde aterrizan documentos nuevos.
- 📜 Resumen legible de un lote `.txt`, `.md`, `.log`, `.csv`, `.json`.
- 🔄 Base para pipelines más complejos (clasificación, ingesta, OCR).

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `scan_dropbox` | `filesystem.list_directory` | Inventario plano de `dropbox_path`. |
| 2 | `classify_dropbox` | `filesystem.classify_file_inventory` | Agrega por extensión + identifica archivo mayor. |
| 3 | `summarize_texts` | `filesystem.summarize_text_folder` | Lee primeros `max_files=10` archivos compatibles, guarda preview de `max_chars_per_file=500` chars + conteo de líneas. |
| 4 | `write_pipeline_report` | `filesystem.write_json` | Reporte con inventory, stats y summaries. |

## ⚙️ Configuración

```json
{ "dropbox_path": "data/dropbox/inbox" }
```

Parámetros del paso `summarize_texts` (en manifest):
- `max_files = 10` — máximo a previsualizar.
- `max_chars_per_file = 500` — chars por archivo.

## 📋 Requisitos

- ✅ Solo Python stdlib.
- ✅ Permisos de lectura sobre `dropbox_path`.

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": [
    "filesystem.list_directory", "filesystem.classify_file_inventory",
    "filesystem.summarize_text_folder", "filesystem.write_json"
  ],
  "allowed_paths": ["data/dropbox", "output/reports"],
  "max_runtime_seconds": 60
}
```

## ⚠️ Limitaciones

- ❌ Solo lee texto plano: `.txt`, `.md`, `.log`, `.csv`, `.json`. **No PDFs ni Word**.
- ❌ No mueve ni borra archivos. Si quieres rotar, añade `filesystem.move_file`.
- ⚠️ Los previews quedan en el reporte JSON.

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Carpeta de entrada | `dropbox_path` en config |
| Cuántos archivos | `max_files` en manifest |
| Chars por archivo | `max_chars_per_file` en manifest |
| Extensiones soportadas | Editar `actions/filesystem.py:summarize_text_folder` |

## 📤 Salidas

- 📊 `output/reports/document_drop_pipeline_<ts>.json` con `inventory`, `stats`, `summary`.

## ⚡ Ejecución

```bash
flujo run flows/04_document_drop_pipeline
# Programar cada 30 min: */30 * * * *
```
