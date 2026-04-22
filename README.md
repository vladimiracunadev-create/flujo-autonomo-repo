# flujo-autonomo-repo-v5

Repositorio operativo de **procesos autónomos reales** para PC.

## Qué incluye

- Panel local para ejecutar procesos, editar configuración, revisar historial y activar scheduler.
- Motor declarativo basado en `manifest.json`, con `when`, `transitions`, retries y límite de pasos.
- Persistencia operativa en SQLite, snapshots JSON y logs JSONL.
- Acciones para filesystem, sistema, pantalla, UI, HTTP, reglas y visión.
- Caso visual tri-modo: OCR, visión y modo híbrido.
- Proveedor de visión desacoplado: `mock`, `openai_compatible` u `ollama`.
- Acciones UI con `dry_run` para probar procesos sin tocar el escritorio real.

## Arranque

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# o .venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m app.server
```

Panel:

```text
http://127.0.0.1:8787
```

## CLI

```bash
python -m engine.runner list
python -m engine.runner run flows/05_system_healthcheck
python -m engine.runner scheduler --interval 2
```

`list` no requiere inicializar SQLite ni cargar dependencias opcionales de acciones. Esto permite inspeccionar los flujos incluso antes de instalar todo el entorno.

## Validación rápida

Valida manifests, acciones registradas y transiciones sin dependencias externas:

```bash
python scripts/validate_project.py
```

Prueba integral con SQLite, scheduler y flujos reales:

```bash
python scripts/smoke_test.py
```

## Estructura

```text
/app        Panel local
/actions    Acciones ejecutables por los flujos
/engine     Motor, loader, scheduler, templates y persistencia
/plugins    Analizadores extensibles
/flows      Casos ejecutables
/configs    Configuración por flujo
/db         Base SQLite local
/logs       Eventos técnicos JSONL
/state      Snapshots completos de corrida
/output     Reportes y capturas generadas
/docs       Documentación técnica
```

## Familias vs casos

- **Familia**: categoría conceptual.
- **Caso**: flujo concreto ejecutable.

Cada carpeta dentro de `flows/` es un caso real.

## Branching real

Cada paso puede declarar `when` y `transitions`:

```json
{
  "id": "decide_next",
  "action": "rules.evaluate",
  "save_as": "decision",
  "transitions": [
    {
      "on": "success",
      "when": {"path": "decision.status", "operator": "eq", "value": "hay_archivos"},
      "next": "write_inventory"
    },
    {"on": "success", "next": "write_empty"}
  ]
}
```

## OCR y reglas visuales

- `vision.ocr_image`
- `vision.find_text_in_image`
- `vision.inspect_screen_target`
- `ui.click_bbox`

Para OCR local necesitas **pytesseract** y el binario **Tesseract OCR** instalado en el equipo.

## Flujos destacados

- `01_screen_capture_analyze`
- `02_screen_watchdog_rules`
- `07_browser_assisted_capture`
- `08_ui_macro_recovery`
- `09_branching_document_router`
- `10_screen_ocr_click_recovery`
- `11_screen_tri_mode_operator`

## Modos visuales en v5

El caso `11_screen_tri_mode_operator` soporta:

- **OCR**: `analysis_mode = "ocr"`
- **Visión**: `analysis_mode = "vision"`
- **Híbrido**: `analysis_mode = "hybrid"`

Además admite:

- `vision_provider = "mock"` para pruebas sin IA externa
- `vision_provider = "openai_compatible"` para endpoints compatibles
- `vision_provider = "ollama"` para un modelo local multimodal

Para correrlo sin GUI real puedes usar:

- `image_override` apuntando a una imagen existente
- `ui_dry_run = true`
- `skip_after_capture = true`

## Seguridad operativa

Los flows pueden leer/escribir archivos, abrir URLs, controlar UI y lanzar procesos. Úsalos como automatizaciones locales confiables y revisa cualquier manifest recibido de terceros antes de ejecutarlo.

La acción `ui.launch_process` usa `shell=false` por defecto, valida comandos vacíos y soporta `dry_run`.
