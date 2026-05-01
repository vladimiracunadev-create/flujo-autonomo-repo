# Crear Flows

Un flow es un proceso ejecutable dentro de `flows/<nombre>/`. Debe ser comprensible para una persona y válido para el motor (JSON Schema en `schemas/manifest.schema.json`).

## Estructura Mínima

```text
flows/mi_nuevo_flow/
  manifest.json
  context.example.json
  README.md
```

## Manifest

Ejemplo mínimo:

```json
{
  "id": "mi_nuevo_flow",
  "name": "Mi nuevo flow",
  "family": "filesystem",
  "description": "Describe el propósito operativo del flow.",
  "steps": [
    {
      "id": "scan",
      "action": "filesystem.list_directory",
      "params": {"path": "{{ path_override }}", "recursive": false},
      "save_as": "inventory"
    },
    {
      "id": "write_report",
      "action": "filesystem.write_json",
      "params": {
        "path": "output/reports/mi_nuevo_flow_{now}.json",
        "data": {"inventory": "{{ inventory }}"}
      },
      "save_as": "report"
    }
  ]
}
```

## Campos Soportados

| Campo | Nivel | Uso |
| --- | --- | --- |
| `id` | manifest/step | identificador estable; el del manifest debe matchear `^[a-z0-9_]+$` |
| `name` | manifest | nombre humano |
| `family` | manifest | categoría documental |
| `description` | manifest | descripción corta |
| `start_step` | manifest | paso inicial opcional |
| `max_steps_per_run` | manifest | guardrail contra loops |
| `allowed_actions` | manifest | sandbox: lista blanca de acciones |
| `required_secrets` | manifest | sandbox: variables de entorno o secretos requeridos |
| `allowed_paths` | manifest | sandbox: prefijos de ruta donde el flow puede leer/escribir |
| `max_runtime_seconds` | manifest | sandbox: corta la corrida si se excede |
| `action` | step | acción registrada |
| `params` | step | argumentos renderizados con contexto |
| `save_as` | step | clave de contexto para el resultado |
| `when` | step/transition | condición |
| `retries` | step | reintentos |
| `transitions` | step | rutas explícitas |

## Sandbox Por Flow

Declara la política directamente en el manifest. El motor la aplica antes y durante la corrida:

```json
{
  "id": "auditoria_segura",
  "name": "Auditoría",
  "allowed_actions": [
    "filesystem.list_directory",
    "filesystem.write_json",
    "rules.evaluate",
    "notify.send"
  ],
  "allowed_paths": ["data/auditorias", "output/reports"],
  "required_secrets": ["AUDIT_API_KEY"],
  "max_runtime_seconds": 60,
  "steps": [...]
}
```

Comportamiento:

- Si falta un secret de `required_secrets`, el flow ni siquiera arranca.
- Si un paso usa una acción fuera de `allowed_actions`, queda `failed` con `error.kind = "sandbox_violation"`.
- Si un parámetro tipo path apunta fuera de `allowed_paths` (tras resolver templates), el paso falla.
- Si la corrida total supera `max_runtime_seconds`, el siguiente paso aborta.

## Templates

Los parámetros pueden leer contexto:

```json
{"path": "{{ inventory.files }}"}
```

También pueden usar `{now}` para timestamps:

```json
{"path": "output/reports/reporte_{now}.json"}
```

## Condiciones

Operadores disponibles:

- `eq`, `ne`
- `gt`, `gte`, `lt`, `lte`
- `contains`, `in`
- `exists`, `not_exists`
- `truthy`, `falsy`
- `regex`

También puedes componer:

```json
{
  "all": [
    {"path": "inventory.total_files", "operator": "gt", "value": 0},
    {"path": "decision.status", "operator": "eq", "value": "ok"}
  ]
}
```

## Transiciones

```json
"transitions": [
  {
    "on": "success",
    "when": {"path": "decision.status", "operator": "eq", "value": "hay_archivos"},
    "next": "procesar"
  },
  {"on": "success", "next": "sin_archivos"},
  {"on": "failure", "next": "recuperar"}
]
```

Eventos soportados:

- `success`
- `failure`
- `any`

Para terminar:

```json
{"on": "success", "end": true}
```

## Acciones Disponibles

Listado completo en [docs/FAMILIAS_Y_CASOS.md](FAMILIAS_Y_CASOS.md). Algunas relevantes nuevas:

- `notify.send` — backends `log`, `file` o `webhook`. Para Slack/Discord usa `backend: webhook` con el URL como `target`. Soporta tokens via `@secret:NOMBRE`.

Para añadir tus propias acciones desde un paquete externo, consulta [docs/EXTENSION.md](EXTENSION.md).

## README Del Flow

Cada README debe incluir:

- propósito;
- familia;
- cuándo usarlo;
- contexto esperado;
- salida generada;
- requisitos o riesgos;
- comando de ejemplo si aplica.

## Checklist Antes De Subir

```bash
python scripts/validate_project.py    # JSON Schema + acciones + transitions
pytest -k <area>                       # tests relacionados
python -m engine.runner list           # smoke rápido sin DB
```

Si el flow tiene efectos reales:

1. prueba con carpeta o imagen de ejemplo;
2. usa `dry_run` cuando haya UI;
3. revisa `output/`, `state/` y `logs/`;
4. documenta cualquier dependencia externa;
5. considera declarar `allowed_actions` y `allowed_paths` para auditarlo después.
