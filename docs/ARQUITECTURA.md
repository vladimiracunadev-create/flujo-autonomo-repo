# Arquitectura v5

## Capas

1. **Panel local (`app/`)**
   - índice principal
   - ejecución manual
   - configuración por flujo
   - histórico y detalle

2. **Motor (`engine/`)**
   - carga de manifests
   - orquestación
   - branching
   - scheduler
   - persistencia a SQLite + JSON/JSONL

3. **Acciones (`actions/`)**
   - filesystem
   - sistema
   - UI
   - pantalla
   - visión

4. **Plugins (`plugins/`)**
   - metadatos de imagen
   - heurística mock
   - OCR local

## Persistencia

- `db/runs.db`: consulta rápida operativa.
- `state/*.json`: snapshot completo por corrida.
- `logs/*.jsonl`: eventos técnicos detallados.

## Estado de ejecución

Cada corrida guarda:

- estado global
- ruta seguida
- pasos ejecutados
- contexto final
- salidas detectadas
- error final si existe

## Scheduler

El scheduler revisa `schedules` en SQLite y dispara corridas cuando llega `next_run_at`.


## Extensión v5: análisis visual tri-modo

El repositorio incorpora un flujo de pantalla que puede analizar con OCR, visión o modo híbrido.
Esto mantiene la ejecución programada en el motor, y deja la IA como componente opcional de análisis.
