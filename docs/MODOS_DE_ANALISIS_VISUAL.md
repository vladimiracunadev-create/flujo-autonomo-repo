# Modos De Análisis Visual

El sistema puede analizar una pantalla o imagen en tres modos: OCR, visión o híbrido. La elección depende del tipo de interfaz, la estabilidad del texto y el nivel de trazabilidad requerido.

## OCR

Usa `pytesseract` para extraer texto estructurado y bounding boxes.

Conviene cuando:

- el objetivo se reconoce por texto visible;
- los labels o botones son estables;
- se necesita auditoría textual;
- se quiere operación local sin proveedor externo.

Requisitos:

- paquete Python `pytesseract`;
- binario Tesseract OCR instalado en el equipo;
- imagen legible.

## Visión

Usa un proveedor multimodal para interpretar la imagen completa.

Proveedores soportados:

- `mock`: no llama a IA externa; sirve para probar el flujo y la trazabilidad.
- `openai_compatible`: endpoint estilo `/chat/completions`.
- `ollama`: endpoint local compatible con modelos multimodales.

Conviene cuando:

- importan layout, iconos o contexto visual;
- el texto no basta para decidir;
- la pantalla cambia de forma no textual;
- el operador quiere usar un modelo local/remoto.

## Híbrido

Ejecuta OCR y visión, luego elige el bounding box con prioridad configurable mediante `prefer_source`.

Conviene cuando:

- a veces hay texto claro y a veces no;
- OCR entrega trazabilidad, pero visión mejora comprensión;
- se necesita tolerancia a cambios de UI;
- el proceso debe decidir entre click y recuperación.

## Decisión Práctica

| Situación | Modo recomendado |
| --- | --- |
| botón con texto estable | `ocr` |
| pantalla con iconos o layout importante | `vision` |
| flujo crítico con UI variable | `hybrid` |
| ambiente de prueba sin IA externa | `vision_provider = "mock"` |
| entorno sin escritorio real | `image_override` + `ui_dry_run` |

## Configuración Base Del Caso Tri-Modo

```json
{
  "analysis_mode": "hybrid",
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

## Riesgos

- OCR puede fallar por resolución, idioma, contraste o fuente.
- Un modelo de visión puede devolver JSON incompleto o bounding boxes imprecisos.
- El click real debe usarse solo con `ui_dry_run = false` cuando el operador haya validado coordenadas.
- `fallback_bbox` es útil para continuidad, pero debe tratarse como una decisión configurada, no como detección real.
