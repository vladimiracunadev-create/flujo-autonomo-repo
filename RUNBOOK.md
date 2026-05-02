# 📕 Runbook operativo · Flujo Autónomo

> Procedimientos rápidos para operar el sistema en el día a día.

## 🚀 Levantar el panel

```bash
uv run python -m app.server
# Panel: http://127.0.0.1:8787
# Health: http://127.0.0.1:8787/healthz
```

## 🧹 Reset completo del histórico

```bash
# Para cuando quieres empezar limpio
rm -f db/runs.db
rm -rf logs/* state/* output/screenshots/* output/reports/*
rm -f data/seeds/.used_indices.json
```

La DB se recrea vacía al primer arranque.

## 📊 Verificar estado

```bash
# 0 schedules, 0 runs esperados tras reset
python -c "from engine.database import init_db, list_schedules, list_runs; init_db(); print('schedules:', list_schedules()); print('runs:', len(list_runs()))"
```

## ⚠️ Liberar lock atascado de un flow

```python
# Si un flow quedó marcado como "ejecutándose" pero el proceso murió
from engine.database import force_release_lock
force_release_lock("05_system_healthcheck")
```

## 🔍 Consultas a SQLite directas

```bash
# Top 10 corridas más lentas
sqlite3 db/runs.db "SELECT flow_id, run_id, duration_seconds FROM runs ORDER BY duration_seconds DESC LIMIT 10"

# Errores recientes
sqlite3 db/runs.db "SELECT flow_id, run_id, error_json FROM runs WHERE status='failed' ORDER BY created_at DESC LIMIT 5"

# Outputs producidos por un flow
sqlite3 db/runs.db "SELECT outputs_json FROM runs WHERE flow_id='screen_capture_browser' ORDER BY created_at DESC LIMIT 1"
```

## 🌐 Probar webhook entrante

```bash
# 1. Define el secreto antes de levantar el panel
export FLUJO_WEBHOOK_TOKEN=$(openssl rand -hex 32)

# 2. Reinicia el panel para que tome el secreto
uv run python -m app.server &

# 3. Dispara un flow desde curl
curl -X POST -H "X-Flujo-Token: $FLUJO_WEBHOOK_TOKEN" \
     http://127.0.0.1:8787/api/hook/05_system_healthcheck
```

## 🎯 Override de context vía API

Cualquier flow puede correrse con context distinto sin tocar archivos:

```bash
# Flow 02 capturando una URL diferente
curl -X POST -H "Content-Type: application/json" \
     -d '{"context_overrides": {"target_url": "https://github.com"}}' \
     http://127.0.0.1:8787/api/run/02_screen_capture_browser

# Flow 03 explorando otra carpeta
curl -X POST -H "Content-Type: application/json" \
     -d '{"context_overrides": {"path_override": "C:/Users/me/Documents"}}' \
     http://127.0.0.1:8787/api/run/03_folder_inventory
```

## 🪝 Resetear el tracking del caso 07

El caso 07 elige uno de 100 registros sin repetir. Para empezar de nuevo:

```bash
rm -f data/seeds/.used_indices.json
```

## ⌨️ Atajos del panel

| Tecla | Acción |
| --- | --- |
| `Alt+1..9 / Alt+0 / Alt+- / Alt+=` | Ejecutar flow N |
| `Alt+E` / `Alt+P` / `Alt+H` | Tab Ejecutar / Programadas / Histórico |
| `Alt+M` | Dashboard de Métricas |
| `?` o `F1` | Mostrar ayuda |
| `Esc` | Cerrar modal |

## 🔄 CI verde local antes de un push

```bash
uv run pytest && uv run ruff check . && uv run python scripts/validate_project.py
```

Las tres deben pasar antes de empujar a `main`.

## 🆘 Servicios externos no disponibles

- **Tesseract no instalado**: el OCR analyzer degrada graciosamente devolviendo `status: "unavailable"`.
- **Playwright Chromium no instalado**: `python -m playwright install chromium` lo descarga (~150 MB).
- **pyautogui falta**: instalar con `pip install pyautogui`. En Linux requiere `python3-tk`.

## 📦 Dependencias del proyecto

| Categoría | Lib | Para qué |
| --- | --- | --- |
| Captura escritorio | `mss`, `Pillow` | Caso 01 |
| Sistema | `psutil` | Casos 05, 06 |
| Captura DOM | `playwright` | Caso 02 |
| Form filling | `playwright` | Caso 07 |
| HTTP | `requests` | acciones genéricas |
| Schema | `jsonschema` (extra) | Validador estricto |
| Tests | `pytest`, `pytest-cov` (extra) | Suite |

## 🛡️ Verificar hardening del CI antes de un push grande

Cuando vayas a tocar `.github/workflows/**` o agregar una nueva acción third-party, validá local antes de empujar:

```bash
# 1. Sintaxis YAML de todos los workflows
python -c "import yaml,glob; [yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('.github/workflows/*.yml')]; print('YAML OK')"

# 2. zizmor en local (audita injection / permisos / unpinned)
pip install zizmor==1.5.2
zizmor --persona=auditor .github/workflows/

# 3. actionlint en local
# Linux/Mac: bash <(curl -sSfL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)
./actionlint -color
```

Si zizmor o actionlint marcan algo, **no pushees** sin entender el hallazgo. La política completa está en [SECURITY.md](SECURITY.md) §"Hardening del CI/CD".

## ➕ Agregar una acción third-party nueva al CI

1. Buscar el SHA del tag deseado en el repo upstream (página de releases o `git ls-remote`).
2. En el workflow: `uses: owner/repo@<sha-de-40-chars>  # vX.Y.Z`.
3. El job `pin-check` de [workflow-security.yml](.github/workflows/workflow-security.yml) falla si el SHA no tiene 40 chars hex.
4. Excepciones (allowlist) van en `ALLOWLIST=()` dentro del mismo workflow + justificación en [SECURITY.md](SECURITY.md) §CI.

## 🚨 Rollback de un commit en main

```bash
# Crear commit nuevo que revierte uno previo (preferido sobre force-push)
git revert <sha>
git push origin main
```
