# Changelog

Todas las versiones notables de Flujo Autónomo se documentan acá. El formato sigue
[Keep a Changelog](https://keepachangelog.com/) y la versión sigue [SemVer](https://semver.org/lang/es/).

## [0.3.0] — 2026-05-01

### ✨ UI

- 🎨 **Panel rediseñado a 3 tabs**: `▶ Ejecutar`, `⏰ Programadas`, `📜 Histórico`. Single-page, sin framework, hash-based routing.
- ⚡ **Click-to-run en tiempo real**: nuevo `POST /api/run/<folder>`, spinner, toasts y badge de estado live por card.
- 🖼️ **Detalle de run con thumbnails**: capturas e imágenes generadas se muestran inline; archivos no-imagen como mini-cards.
- 📊 **Dashboard de métricas con KPI cards**: completadas, falladas, en curso, duración promedio.
- 🎨 Diseño refinado con CSS variables, gradientes suaves, animaciones sutiles, responsive con grid auto-fit.

### 🛠️ CI

- ✅ `setup-uv@v3` ahora cachea sobre `pyproject.toml` (antes fallaba buscando `uv.lock`).

### 🧪 Tests

- 5 tests del nuevo panel HTTP (live server contra puerto efímero). Suite total **82 verde**.

---

## [0.2.0] — 2026-05-01

### 🛡️ Sandbox por flow

- `allowed_actions`: lista blanca de acciones por manifest.
- `required_secrets`: variables requeridas antes de iniciar.
- `allowed_paths`: prefijos de ruta donde el flow puede operar.
- `max_runtime_seconds`: corta la corrida si excede tiempo total.
- Las violaciones quedan registradas como `sandbox_violation` en SQLite.

### ⏰ Scheduler con cron

- Nuevo parser cron de 5 campos sin dependencias externas (`engine/cron.py`).
- `next_after()` calcula próxima ejecución; soporta listas, rangos, pasos.
- Tabla `run_locks` en SQLite para evitar ejecución paralela del mismo flow.
- Migración suave para bases preexistentes.

### 📊 Observabilidad

- Endpoints: `/healthz`, `/api/flows`, `/api/runs`, `/api/metrics`, `/metrics` (Prometheus), `/metrics/dashboard`.
- Agregaciones: totales por estado, ventana móvil, top acciones lentas/fallidas/con retries.

### 🔌 Extensibilidad

- `LazyActionRegistry` descubre acciones de terceros via entry-point `flujo.actions`.
- Bóveda de secretos local (`engine/secrets.py`): env > file con prioridad.
- Acción `notify.send` con backends `log`, `file` y `webhook`. Tokens via `@secret:NOMBRE`.
- Webhook entrante `POST /api/hook/<folder>` autenticado por `FLUJO_WEBHOOK_TOKEN`.

### 🧪 Calidad

- `pyproject.toml` con extras `dev`, `schema` y entry-points para CLI (`flujo`, `flujo-panel`, `flujo-validate`).
- JSON Schema canónico en `schemas/manifest.schema.json`.
- Suite **77 tests pytest** (template, conditions, loader, registry, orquestador, sandbox, cron, locks, métricas, secrets, notify, schema vs manifests reales).
- CI con `uv` en matriz Linux/Windows × Python 3.10–3.12 + lint ruff + smoke job.

### 📚 Documentación

- 9 docs actualizados + 3 nuevos: `METRICAS.md`, `INTEGRACIONES.md`, `EXTENSION.md`.

---

## [0.1.0] — Versión inicial

- Motor declarativo `manifest.json` con `when`, `transitions`, retries y `max_steps_per_run`.
- Panel local en `127.0.0.1:8787`, persistencia en SQLite + JSON snapshots + JSONL events.
- 11 flows ejecutables: filesystem, sistema, navegador, pantalla, OCR, visión, branching documental.
- CLI `python -m engine.runner` con `list`, `run`, `scheduler`.
- Validador estructural de manifests.
- Smoke test integral.
