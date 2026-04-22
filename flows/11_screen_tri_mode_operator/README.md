# 11 Screen Tri Mode Operator

**Familia:** pantalla / escritorio.

Caso visual más completo del repositorio. Usa imagen existente o captura real, analiza objetivo en modo OCR, visión o híbrido, decide click o recuperación y deja evidencia completa.

## Cuándo Usarlo

- comparar OCR contra visión multimodal;
- probar automatización visual sin GUI mediante `image_override`;
- operar con `dry_run` antes de permitir clicks reales;
- documentar decisiones visuales con diagnóstico.

## Modos

| Modo | Uso |
| --- | --- |
| `ocr` | texto visible, labels estables, auditoría local |
| `vision` | layout, iconos o contexto visual |
| `hybrid` | OCR + visión con prioridad configurable |

## Proveedores

- `mock`: pruebas sin IA externa.
- `openai_compatible`: endpoint estilo `/chat/completions`.
- `ollama`: endpoint local tipo `http://127.0.0.1:11434/api/chat`.

## Contexto

```json
{
  "analysis_mode": "vision",
  "query_text": "Guardar",
  "vision_provider": "mock",
  "prefer_source": "ocr",
  "fallback_bbox": {"left": 35, "top": 35, "width": 230, "height": 85},
  "recovery_hotkey": ["esc"],
  "ui_dry_run": true,
  "skip_after_capture": true,
  "image_override": "tests/assets/sample_ui.png"
}
```

## Salida

- captura o selección de imagen;
- análisis OCR/visión;
- decisión `click` o `recover`;
- resultado de click/hotkey;
- reporte JSON con configuración efectiva.

## Modo Seguro De Prueba

Usa:

- `image_override` con una imagen existente;
- `ui_dry_run = true`;
- `skip_after_capture = true`.

Así el flow corre completo sin interactuar con el escritorio real.

## Ejecución

```bash
python -m engine.runner run flows/11_screen_tri_mode_operator
```
