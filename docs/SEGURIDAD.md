# 🛡️ Seguridad Operativa

> Sandbox declarativo por flow, bóveda de secretos y modelo de confianza.

![Seguridad](assets/cover-flujo-autonomo.svg)

Flujo Autónomo ejecuta automatizaciones locales. Eso lo hace útil, pero también exige tratar cada manifest como código operativo. Desde la versión 0.2.0, cada flow declara su propia política de sandbox que el motor hace cumplir.

> [!WARNING]
> Si vas a aceptar manifests de terceros, **siempre revísalos antes de ejecutarlos**. El sandbox declarativo limita el daño pero no es aislamiento OS-level.

---

## 🤝 Modelo De Confianza

El sistema asume que:

- el operador controla el repositorio;
- los manifests vienen de una fuente confiable o pasan revisión;
- el panel corre en localhost;
- las acciones se ejecutan con permisos del usuario local.

No asume:

- aislamiento OS-level por proceso;
- control multiusuario;
- revisión semántica completa de comandos arbitrarios.

---

## 🔒 Sandbox Por Flow

El motor aplica cuatro controles declarativos. Detalle en [engine/sandbox.py](../engine/sandbox.py):

| Campo del manifest | Control |
| --- | --- |
| `allowed_actions` | lista blanca: cualquier acción fuera de la lista bloquea el paso con `sandbox_violation` |
| `required_secrets` | el flow no arranca si falta alguna variable (env > `secrets/secrets.json`) |
| `allowed_paths` | tras resolver templates, todo `params.path` (y similares) debe estar bajo uno de los prefijos |
| `max_runtime_seconds` | la corrida aborta si excede este tiempo total |

Ejemplo:

```json
{
  "id": "auditoria",
  "name": "Auditoría",
  "allowed_actions": ["filesystem.list_directory", "filesystem.write_json", "notify.send"],
  "allowed_paths": ["data/auditorias", "output/reports"],
  "required_secrets": ["AUDIT_API_KEY"],
  "max_runtime_seconds": 60,
  "steps": [...]
}
```

Las violaciones se registran como evento `step_blocked` o `flow_blocked`, y la corrida queda en `failed` con `error.kind = "sandbox_violation"`. El validador (`scripts/validate_project.py`) revisa además que las acciones declaradas en `allowed_actions` no excluyan acciones que el flow realmente usa.

---

## 🔐 Bóveda De Secretos

`engine/secrets.py` resuelve en orden:

1. `os.environ[NOMBRE]`.
2. `secrets/secrets.json` (carpeta ignorada por git).

API:

```python
from engine.secrets import get_secret, set_secret
set_secret("MY_TOKEN", "abc")
get_secret("MY_TOKEN")
```

Las acciones que aceptan tokens (p. ej. `notify.send` con `backend=webhook`) admiten la sintaxis `@secret:NOMBRE` para no embeberlos en el manifest.

---

## 🪝 Webhook De Entrada

El endpoint `POST /api/hook/<folder>` permite disparar flows externamente. Está deshabilitado por defecto: sólo acepta peticiones cuando el secreto `FLUJO_WEBHOOK_TOKEN` está definido y el header `X-Flujo-Token` coincide.

```bash
export FLUJO_WEBHOOK_TOKEN=$(openssl rand -hex 32)
curl -X POST -H "X-Flujo-Token: $FLUJO_WEBHOOK_TOKEN" \
     http://127.0.0.1:8787/api/hook/05_system_healthcheck
```

Si vas a exponerlo más allá de localhost, ponlo detrás de un reverse proxy con TLS y autorización adicional.

La comparación del token usa `hmac.compare_digest` (constant-time, CWE-208).

---

## 🛂 Autorización Del Panel HTTP (post-2026-06)

Todos los endpoints `POST` mutadores (`/api/run/`, `/run`, `/flow/<folder>/config`, `/flow/<folder>/schedule`, `/api/form/submit`) pasan por `_authorize_mutation` antes de ejecutar. Tiene dos modos:

### Modo 1 — Token explícito (recomendado para máquinas compartidas)

Si la variable de entorno `FLUJO_PANEL_TOKEN` está definida, **toda** mutación exige el header `X-Flujo-Token` con valor exacto:

```bash
export FLUJO_PANEL_TOKEN=$(openssl rand -hex 32)
curl -X POST -H "X-Flujo-Token: $FLUJO_PANEL_TOKEN" \
     http://127.0.0.1:8787/api/run/05_system_healthcheck
```

Sin el header o con valor distinto → `401 Unauthorized` (comparación constant-time).

### Modo 2 — Sin token (panel local sin fricción, default)

Cuando `FLUJO_PANEL_TOKEN` no está seteado, se aplican defensas anti-CSRF y anti-DNS-rebinding:

1. El header `Host` debe ser loopback (`127.0.0.1`, `localhost`, `[::1]`).
2. Si la request trae `Origin`, debe igualar `http://<Host>`.
3. Si trae `Referer`, debe empezar con `http://<Host>/`.

Esto bloquea el caso real: un sitio web malicioso visitado por el operador que intenta `fetch('http://127.0.0.1:8787/api/run/X')` — el browser siempre envía `Origin` en fetch cross-site, así que es rechazado con 401. Scripts locales (curl, tests) que no envían `Origin` siguen funcionando.

> [!IMPORTANT]
> Si vas a binder el panel a una IP no loopback, **es obligatorio** setear `FLUJO_PANEL_TOKEN`. El modo 2 asume loopback y rechaza el resto.

---

## 🚫 Lo Que `ui.launch_process` Ya No Hace

Desde la auditoría 2026-06, el parámetro `shell=True` está **deshabilitado por código** y lanza `ValueError`. Razón: cualquier flow que aceptara `shell=True` con un `command` parcialmente proveniente de contexto (vía `context_overrides` del panel, vía webhook, vía variable rendered) era RCE directa (CWE-78). Si necesitás argumentos complejos, pasalos como string tokenizable por `shlex.split`.

```jsonc
// ✅ permitido
{"action": "ui.launch_process", "params": {"command": "notepad C:\\Users\\me\\nota.txt"}}

// ❌ rechazado en runtime con ValueError
{"action": "ui.launch_process", "params": {"command": "...", "shell": true}}
```

---

## 📁 Endpoint `/file` Endurecido

`GET /file?path=<rel_o_abs>` sirve archivos del workspace para previews del panel. Tras la auditoría 2026-06:

- Validación de ruta usa `Path.is_relative_to(ROOT.resolve())` (antes: `str.startswith`, vulnerable a bypass por prefijo `*-evil`).
- Allowlist de extensiones servibles: bloquea `.html .htm .xhtml .xml .svg .js .mjs .css` para impedir XSS reflejado desde el mismo origen.
- Respuesta lleva `X-Content-Type-Options: nosniff`.

---

## ⚠️ Superficies Sensibles

| Superficie | Riesgo | Control actual |
| --- | --- | --- |
| 📁 Filesystem | leer, mover o escribir archivos | `allowed_paths` por flow + `.gitignore` para salidas |
| 🖱️ UI automation | clicks, hotkeys y escritura | `dry_run` en acciones UI críticas |
| ⚙️ Procesos | ejecución local | `ui.launch_process` con `shell=True` **rechazado por código** (post-2026-06) |
| 🌐 Red | requests HTTP | acción explícita; los webhooks salientes resuelven token vía `@secret:` |
| 📷 Pantalla | captura visible | ejecución local y archivos ignorados |
| 👁️ Visión externa | envío de imágenes | proveedor configurable y `mock` por defecto en pruebas |
| 🪝 Webhook entrante | ejecución remota | token obligatorio + sólo localhost por defecto |

---

## ✅ Reglas De Uso Seguro

1. Revisa `manifest.json` antes de ejecutar un flow nuevo.
2. Ejecuta `python scripts/validate_project.py` antes de correr.
3. Declara `allowed_actions` y `allowed_paths` en flows en producción.
4. Mantén `ui_dry_run = true` mientras calibras coordenadas.
5. No actives scheduler en flows que todavía no probaste manualmente.
6. **No guardes API keys en `configs/`**; usa la bóveda o variables de entorno.
7. No apuntes acciones filesystem a carpetas críticas sin backup.
8. Trata `fallback_bbox` como configuración manual, no como detección.

---

## ⚡ Acciones Con Mayor Cuidado

- `filesystem.move_file`
- `filesystem.write_json`
- `ui.launch_process`
- `ui.click`
- `ui.click_bbox`
- `ui.hotkey`
- `http.fetch_url`
- `screen.capture_screenshot`
- `notify.send` con `backend=webhook` (el token sale del proceso)

---

## 🎯 Buenas Prácticas Para Manifests

- Prefiere rutas dentro del workspace.
- Escribe reportes en `output/reports/`.
- Escribe capturas en `output/screenshots/`.
- Evita `overwrite=true` salvo que esté justificado.
- Incluye transiciones de recuperación para pasos frágiles.
- Usa `max_steps_per_run` y `max_runtime_seconds` cuando haya loops o llamadas externas.
- Deja contexto de ejemplo sin secretos.
- Para flows críticos, declara `allowed_actions` aunque sea redundante: documenta el alcance.

---

## 📊 Datos Sensibles

Los archivos generados pueden contener:

- rutas locales;
- capturas de pantalla;
- texto extraído por OCR;
- nombres de procesos;
- respuestas de servicios externos;
- errores con detalles del entorno.

Por eso `db/*.db`, `logs/*.jsonl`, `state/*.json`, `output/**/*.json`, `output/**/*.png` y `secrets/*.json` están ignorados por git.

---

## 🛡️ Hardening Del CI/CD

El repositorio ejecuta acciones reales sobre tu escritorio. Eso significa que un commit malicioso fusionado a `main` es RCE local en cuanto haces `git pull`. Por eso el CI se trata como superficie de ataque crítica y aplica las siguientes capas:

| Capa | Detalle | Archivo |
| --- | --- | --- |
| 🔗 Pin a SHA | Toda acción third-party va pinned a commit SHA, no a tag | [.github/workflows/](../.github/workflows/) |
| 🔐 Sin credenciales persistentes | `persist-credentials: false` en todos los `actions/checkout` | ídem |
| ⚖️ Permisos mínimos | `contents: read` por workflow, escala solo en CodeQL | ídem |
| 🚫 Triggers prohibidos | No `pull_request_target`, no `workflow_run` con código mutable | [SECURITY.md](../SECURITY.md) |
| 🧠 SAST | CodeQL `security-extended,security-and-quality` | [security.yml](../.github/workflows/security.yml) |
| 🕵️ Secretos | `detect-secrets==1.5.0` sobre filesystem + últimos 50 commits | ídem |
| 🦠 Trojan Source | CVE-2021-42574 (Unicode bidi) + zero-width / homoglyphs | ídem |
| 🎭 Ofuscación | `exec(base64)`, `eval()` dinámico, `subprocess(shell=True)` interpolado, `pickle.loads`, `__import__` dinámico | ídem |
| 📡 Exfiltración | Discord/Slack/webhook.site/ngrok/pastebin hardcodeados | ídem |
| 📦 Deps Python | `pip-audit==2.7.3` (soft en PR, hard en push/schedule) | ídem |
| 🤖 Workflows mismos | `actionlint` (checksum) + `zizmor==1.5.2` + pin-check propio | [workflow-security.yml](../.github/workflows/workflow-security.yml) |

> [!IMPORTANT]
> Si un PR introduce un `uses:` sin SHA de 40 chars, el job `pin-check` lo rechaza automáticamente. Si necesitas excepción justificada, agrégala a la `ALLOWLIST` en [workflow-security.yml](../.github/workflows/workflow-security.yml) y documenta el porqué en [SECURITY.md](../SECURITY.md) §CI.

Para la política completa con SHAs activos y procedimiento de revisión, ver [SECURITY.md](../SECURITY.md) §"Hardening del CI/CD".

---

## 🎁 Alcance Actual

La 0.2.0 agrega sandbox declarativo, secretos y webhook autenticado. La auditoría 2026-06 endurece el panel (CSRF, path traversal, XSS, shell injection). Para uso multiusuario, integración empresarial o ejecución de manifests no confiables todavía haría falta:

- aislamiento OS-level por acción (subproceso restringido, contenedor);
- perfiles de permisos por usuario en el panel (hoy es token único);
- auditoría firmada y verificación de integridad de manifests.

---

## 📋 Auditoría 2026-06 — Hallazgos Y Fixes

Resumen de la auditoría interna del 2026-06-01 y su cierre:

| # | Severidad | CWE | Hallazgo | Fix aplicado |
| --- | --- | --- | --- | --- |
| 1 | 🔴 Crítica | 352 + 78 | CSRF en POSTs → RCE vía `launch_process` o `set_flow_config` | `_authorize_mutation` (token o Origin loopback) |
| 2 | 🔴 Crítica | 78 | `subprocess.Popen(command, shell=True)` en `ui.launch_process` | Rama eliminada; `shell=True` lanza `ValueError` |
| 3 | 🟠 Alta | 306 | `/api/run/`, `/run`, `/flow/.../config`, `/flow/.../schedule`, `/api/form/submit` sin auth | Mismo `_authorize_mutation` |
| 4 | 🟠 Alta | 22 | Path traversal en `/file` por `str.startswith` (bypass `*-evil`) | `Path.is_relative_to()` + allowlist de extensiones |
| 5 | 🟠 Alta | 79 | XSS en `status.innerHTML` con `data.error/name` no escapados | Helper `_esc()` en cliente, escape de strings dinámicos |
| 6 | 🟡 Media | 208 | Comparación de token con `==` (timing attack) | `hmac.compare_digest` |
| 7 | 🟡 Media | 1104 | Dependencias sin pinear | Cotas `>=X,<Y` en `pyproject.toml` y `requirements.txt` |
| 8 | 🟢 Baja | 117 | `/file` servía cualquier MIME guess (vector XSS reflejado) | Allowlist + `X-Content-Type-Options: nosniff` |

Cobertura de regresión: [`tests/test_security_hardening.py`](../tests/test_security_hardening.py).
