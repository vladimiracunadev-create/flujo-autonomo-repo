# Changelog

Todas las versiones notables de Flujo Autónomo se documentan acá. El formato sigue
[Keep a Changelog](https://keepachangelog.com/) y la versión sigue [SemVer](https://semver.org/lang/es/).

## [0.4.0] — 2026-05-02

### ✨ Nuevos casos operativos

- 🌐 **02 `screen_capture_browser`** (era 12): captura DOM con Playwright headless. Tiene **input inline en la card** para escribir la URL, atajo `Alt+2` abre modal pidiendo URL.
- 📋 **07 `browser_form_filler`**: operación avanzada sobre formularios web reales.
  - Lanza Chromium **visible** (`headless: false` por defecto), navega a `data/web/form_demo.html` (10 campos: nombre, apellido, email, teléfono, dirección, ciudad, país select, fecha nacimiento, profesión, comentario textarea).
  - Carga **dataset de 100 registros estables** (`data/seeds/form_seeds.json`) y elige uno **al azar sin repetir** entre corridas. Tracking persistente en `data/seeds/.used_indices.json` (ignorado por git). Cuando se agotan los 100, reset automático.
  - Llena los 10 campos uno por uno con `slow_mo=250ms` (visualmente observable), submit, espera validación JS de la página y captura `validation_text` + `submitted_payload` renderizado.
  - **Sin PNG**: solo datos. El JSON resultado queda en `output/reports/` y se muestra en el detalle del run.

### 🗑️ Eliminados (decisión consciente tras auditoría honesta)

- ❌ `02_screen_watchdog_rules` — heurística de brillo demasiado simple, no aportaba valor real.
- ❌ `07_browser_assisted_capture` — redundante con `02_screen_capture_browser` (Playwright es mejor).
- ❌ `08_ui_macro_recovery` — wrapper trivial sobre `ui.hotkey`, sin caso de uso único.
- ❌ `09_branching_document_router` — era demo del feature `transitions`, no caso productivo.
- ❌ `10_screen_ocr_click_recovery` — requería Tesseract instalado para tener valor real.
- ❌ `11_screen_tri_mode_operator` — alta complejidad de mantenimiento vs valor entregado.

### 🎨 UI

- ⌨️ **Atajos de teclado** en el panel: `Alt+1..Alt+=` para ejecutar flow N, `Alt+E/P/H/M` navegación, `?` o `F1` para modal de ayuda, `Esc` para cerrar.
- 📋 Cada card muestra su atajo como `<kbd>` en la esquina.
- 🔍 **Detalle de run rediseñado**:
  - Imagen capturada **prominente** (hero) con **lightbox** al hacer click.
  - Bloque "Qué pasó en esta corrida" con **resumen inteligente** específico por flow (RGB swatch, mini-tabla de procesos, lista de archivos, etc).
  - Pasos **clickeables** abren modal con resultado completo del paso.
  - Eventos técnicos y contexto crudo **colapsables** en `<details>` (no contaminan la vista).
- 📊 **Dashboard del flow** (`/flow/<folder>`):
  - Hero card con descripción + ejecutar inline.
  - 5 KPI cards (total / OK / fail / avg / scheduler).
  - **Grid visual** de últimas 12 corridas con preview (PNG real o claves del JSON).
- ⊘ Pasos de **rama no tomada** ahora se muestran como `NOT_TAKEN` con borde dashed (antes confundían con `PENDING`).

### 🔌 Override de context vía API

- `POST /api/run/<folder>` ahora acepta body JSON `{"context_overrides": {...}}` que se mergea con el context del flow. Usado por:
  - Flow 02: `target_url` desde input inline o modal.
  - Flow 03: `path_override` desde input inline o modal con sugerencias.
  - Flow 07: `headless`, `slow_mo_ms`, etc.

### 🛡️ Endpoint nuevo

- `POST /api/form/submit` recibe el JSON desde la página `form_demo.html` y lo persiste en `output/reports/form_submission_panel_<ts>.json`.

### 🐛 Bugs arreglados

- `extract_existing_paths` fallaba en Linux con `OSError: File name too long` cuando el state contenía strings largos (descripciones de 250+ chars). Fix: heurística de longitud + `try/except OSError`.
- OCR analyzer detecta ahora si Tesseract binario falta y devuelve `status: "unavailable"` en lugar de crashear.
- CSS `step-row`: las duraciones quedaban fuera del card verde — grid simplificado.
- Layout `two-col` se rompía por overflow horizontal del `<pre>` — fix con `min-width: 0` y `pre { white-space: pre-wrap }`.
- `setup-uv@v3` en CI fallaba buscando `uv.lock` inexistente — fix con `cache-dependency-glob: pyproject.toml`.

### 🛠️ CI / Calidad

- Nuevo workflow `security.yml`: CodeQL, detect-secrets, pip-audit, schedule semanal.
- Nuevo workflow `dependency-hygiene.yml`: detección de paquetes desactualizados.
- Nuevo workflow `markdown-docs.yml`: validación de links internos en MDs.
- Nuevo `.github/dependabot.yml`: actualización automática de pip + actions.

### 📚 Docs

- Nuevos: `LICENSE` (MIT), `SECURITY.md` (política de reporte), `CONTRIBUTING.md`, `RUNBOOK.md`.
- Manual de usuario actualizado con flow 02 (Playwright) y flow 07 (form filler).
- `FAMILIAS_Y_CASOS.md`: matriz de compatibilidad reducida a 7 flows reales.

### 🔧 Otros

- Acción `browser.capture_page` (Playwright) registrada (28 → 29 acciones tras agregar `browser.fill_form`).
- 100 seeds de datos sintéticos en `data/seeds/form_seeds.json`.

---

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
