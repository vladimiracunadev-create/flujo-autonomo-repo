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

---

## ⚠️ Superficies Sensibles

| Superficie | Riesgo | Control actual |
| --- | --- | --- |
| 📁 Filesystem | leer, mover o escribir archivos | `allowed_paths` por flow + `.gitignore` para salidas |
| 🖱️ UI automation | clicks, hotkeys y escritura | `dry_run` en acciones UI críticas |
| ⚙️ Procesos | ejecución local | `ui.launch_process` con `shell=false` por defecto |
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

## 🎁 Alcance Actual

La 0.2.0 agrega sandbox declarativo, secretos y webhook autenticado. Para uso multiusuario, integración empresarial o ejecución de manifests no confiables haría falta:

- aislamiento OS-level por acción (subproceso restringido, contenedor);
- autenticación del panel (más allá del token de webhook);
- perfiles de permisos por usuario;
- auditoría firmada y verificación de integridad de manifests.
