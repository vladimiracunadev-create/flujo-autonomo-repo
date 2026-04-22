# Operación

Esta guía describe cómo usar Flujo Autónomo en un entorno local sin asumir infraestructura externa.

## Preparación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Panel Local

```bash
python -m app.server
```

Abre:

```text
http://127.0.0.1:8787
```

Desde el panel puedes:

- ver todos los flows;
- ejecutar un flow manualmente;
- editar el contexto operativo guardado en `configs/`;
- activar/desactivar scheduler por flow;
- revisar historial y detalle de corridas;
- abrir archivos generados dentro del workspace.

## CLI

Listar flows:

```bash
python -m engine.runner list
```

Ejecutar un flow:

```bash
python -m engine.runner run flows/05_system_healthcheck
```

Ejecutar con contexto explícito:

```bash
python -m engine.runner run flows/03_folder_inventory --context configs/03_folder_inventory.json
```

Levantar scheduler:

```bash
python -m engine.runner scheduler --interval 2
```

## Contexto Operativo

El contexto se carga en este orden:

1. archivo pasado por `--context`;
2. `configs/<folder>.json`;
3. `flows/<folder>/context.user.json`;
4. `flows/<folder>/context.example.json`;
5. `{}` si no existe nada.

Recomendación:

- usa `context.example.json` como contrato documentado;
- usa `configs/` para operación local;
- evita commitear secretos o rutas sensibles.

## Salidas

| Carpeta | Contenido |
| --- | --- |
| `db/runs.db` | historial consultable |
| `state/*.json` | estado completo de cada corrida |
| `logs/*.jsonl` | eventos técnicos |
| `output/reports/*.json` | reportes físicos |
| `output/screenshots/*.png` | capturas |

## Flujo Recomendado De Operación

1. Ejecuta `python scripts/validate_project.py`.
2. Lista flows con `python -m engine.runner list`.
3. Revisa/ajusta `configs/<flow>.json`.
4. Ejecuta primero con `dry_run` si hay UI o clicks.
5. Revisa detalle de corrida en panel.
6. Activa scheduler solo cuando el flow ya corrió bien manualmente.

## Criterios Para Scheduler

Activa scheduler cuando:

- el flow es idempotente o tolera repetición;
- sus salidas no pisan archivos críticos;
- no requiere supervisión humana inmediata;
- no ejecuta clicks reales sin haber sido probado.

Evita scheduler cuando:

- el flow modifica archivos de alto valor;
- usa `ui.launch_process` con comandos dinámicos;
- depende de una ventana exacta no controlada;
- se está ajustando `fallback_bbox` o coordenadas.
