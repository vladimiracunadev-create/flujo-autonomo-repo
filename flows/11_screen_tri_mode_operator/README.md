# 11_screen_tri_mode_operator

**Familia:** pantalla / escritorio.

Caso operativo de pantalla con **tres modos de análisis**:

- **OCR**: extrae texto localmente con `pytesseract`.
- **Visión**: usa un proveedor multimodal (`mock`, `openai_compatible` u `ollama`).
- **Híbrido**: intenta OCR y visión, y elige una fuente prioritaria (`prefer_source`).

## Qué hace

1. Usa una imagen existente si se configuró `image_override`, o captura pantalla si no existe.
2. Analiza el objetivo visual según `analysis_mode`.
3. Si encuentra bounding box, hace click (o `dry_run`).
4. Si no encuentra objetivo, ejecuta una recuperación por hotkey (o `dry_run`).
5. Guarda un reporte completo con resultados, diagnósticos y configuración efectiva.

## Modos

### OCR
- Recomendado cuando el objetivo se reconoce por texto visible.
- Más determinista para auditoría.
- Requiere `pytesseract` y el binario Tesseract OCR en el equipo.

### Visión
- Recomendado cuando importa el layout de pantalla, íconos o contexto visual.
- Puede trabajar con proveedores multimodales externos o locales.
- `mock` sirve para probar el flujo sin IA externa.

### Híbrido
- Une OCR + visión.
- Sirve cuando el texto no siempre aparece claro o la detección visual necesita refuerzo.
- `prefer_source` decide cuál bbox usar primero cuando ambos detectan algo.

## Proveedores de visión

- `mock`: sin OCR ni IA externa; útil para pruebas del proceso.
- `openai_compatible`: endpoint estilo `/chat/completions`.
- `ollama`: endpoint local tipo `http://127.0.0.1:11434/api/chat`.

## Modo prueba sin escritorio

Para pruebas automatizadas o entornos sin GUI:

- configura `image_override` con una imagen existente
- deja `ui_dry_run = true`
- deja `skip_after_capture = true`

Así el flujo corre completo, guarda histórico y no intenta interactuar con el escritorio real.
