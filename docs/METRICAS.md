# 📊 Métricas Operativas

> Endpoints, dashboard HTML y exposición Prometheus para observabilidad.

![Métricas](assets/cover-automa-pc.svg)

El panel expone agregaciones sobre las tablas `runs` y `steps` de SQLite. Todo se calcula on-demand: no hay un proceso de agregación separado.

## Endpoints

| Endpoint | Formato | Uso |
| --- | --- | --- |
| `GET /metrics/dashboard` | HTML | vista resumida con tablas |
| `GET /api/metrics` | JSON | overview + by_flow para integraciones |
| `GET /metrics` | Prometheus text 0.0.4 | scraping externo |
| `GET /healthz` | JSON | readiness simple |
| `GET /api/flows` | JSON | catálogo |
| `GET /api/runs?flow_id=&limit=` | JSON | corridas filtrables |

## Overview

`GET /api/metrics` devuelve:

```json
{
  "overview": {
    "totals_by_status": {"completed": 42, "failed": 3, "running": 0},
    "average_duration_seconds": 0.83,
    "window": {"size": 200, "completed": 40, "failed": 1, "avg_duration_seconds": 0.79},
    "slowest_actions": [{"action": "vision.analyze_image", "avg_d": 1.42, "c": 12}, ...],
    "retries_top_actions": [...],
    "failed_top_actions": [...]
  },
  "by_flow": [
    {"flow_id": "system_healthcheck", "runs_total": 30, "runs_completed": 29, "runs_failed": 1, "avg_duration_seconds": 0.21, "last_run_at": "..."}
  ]
}
```

## Prometheus

`GET /metrics` produce:

```text
# HELP flujo_runs_total Total de corridas por estado.
# TYPE flujo_runs_total counter
flujo_runs_total{status="completed"} 42
flujo_runs_total{status="failed"} 3
# HELP flujo_run_duration_seconds_avg Duración promedio histórica.
# TYPE flujo_run_duration_seconds_avg gauge
flujo_run_duration_seconds_avg 0.83
flujo_runs_window_completed 40
flujo_runs_window_failed 1
```

Compatible con Prometheus, Grafana Agent o cualquier scraper. No publica histogramas: si los necesitas, integra desde `/api/metrics`.

## Dashboard HTML

`GET /metrics/dashboard` muestra:

- totales por estado y duración promedio histórica;
- tabla por flow (total/OK/fail/avg/última);
- top 10 acciones más lentas;
- top 10 acciones con más reintentos.

## Detalle Por Corrida

El detalle individual sigue siendo útil:

- `GET /run/<flow_id>/<run_id>` — vista completa con steps, eventos y outputs.
- En SQLite las tablas `runs`, `steps` y `events` están indexadas por `run_id` para queries directos.

## Recomendaciones

- Si vas a escrapear con Prometheus, controla la frecuencia (las queries SQLite son baratas pero no gratis).
- Para dashboards persistentes con histórico: copia `db/runs.db` periódicamente a un sistema secundario, o exporta a un CSV.
- Para alertas, suscribe Prometheus a `flujo_runs_total{status="failed"}` y dispara cuando crezca en una ventana.
