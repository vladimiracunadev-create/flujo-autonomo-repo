# 🛡️ Política de Seguridad

## Versiones soportadas

Solo la rama `main` recibe actualizaciones de seguridad activas.

| Versión | Soporte |
| --- | --- |
| `main` (HEAD) | ✅ |
| Anteriores | ❌ |

## Reportar una vulnerabilidad

> [!IMPORTANT]
> **No abras un issue público** para vulnerabilidades. Reporta primero en privado.

Canal preferido: [GitHub Security Advisories](https://github.com/vladimiracunadev-create/flujo-autonomo-repo/security/advisories/new) (privado).

Alternativa: email a `vladimir.acuna.dev@gmail.com` con asunto `[SECURITY]`.

## Qué incluir en tu reporte

1. Descripción del problema y versión afectada (commit SHA si aplica).
2. Pasos reproducibles mínimos.
3. Impacto esperado (lectura/escritura/ejecución/escalamiento).
4. PoC opcional, sin datos reales de terceros.

## Tiempo de respuesta esperado

| Severidad | Acuse | Triaje | Fix objetivo |
| --- | --- | --- | --- |
| 🔴 Crítica (RCE, exfiltración) | 48 h | 5 días | 14 días |
| 🟠 Alta (DoS, bypass de sandbox) | 5 días | 14 días | 30 días |
| 🟡 Media (info disclosure local) | 7 días | 21 días | 60 días |
| 🟢 Baja (hardening) | 14 días | mejor esfuerzo | mejor esfuerzo |

## Alcance

**En alcance**:

- Motor declarativo (`engine/`).
- Acciones built-in (`actions/`).
- Panel HTTP (`app/server.py`) — incluye `/api/run/*`, `/api/hook/*`, `/api/form/submit`.
- Esquemas y validador (`schemas/`, `scripts/validate_project.py`).
- Bypass de la `SandboxPolicy` declarada en un manifest.
- Lectura/escritura fuera de `allowed_paths` en flows que la declaren.

**Fuera de alcance**:

- Vulnerabilidades en dependencias upstream (Pillow, mss, pyautogui, Playwright, etc) — repórtalas a su upstream.
- Ataques que requieran acceso físico al equipo del operador.
- Limitaciones declaradas honestamente en [docs/SEGURIDAD.md](docs/SEGURIDAD.md).

## Hardening recomendado para usuarios

- Mantén el panel atado a `127.0.0.1` (default). No lo expongas en red sin reverse proxy + TLS.
- Define `FLUJO_WEBHOOK_TOKEN` antes de habilitar webhooks entrantes.
- Declara `allowed_actions` y `allowed_paths` en flows productivos.
- Revisa `manifest.json` antes de ejecutar un flow nuevo de origen externo.
- Mantén `db/runs.db`, `output/`, `state/`, `logs/` y `secrets/` ignorados por git (default).

## Hardening del CI/CD (supply chain)

Este repo ejecuta acciones de teclado, mouse y captura de pantalla en el equipo del operador. Un commit malicioso fusionado a `main` se traduce directamente en RCE local cuando el operador hace pull. Por eso el CI se trata como una superficie de ataque crítica.

### Política de acciones de GitHub

1. **Pin a SHA**, no a tag, en toda acción third-party. Los tags (`@v4`, `@main`) son movibles y vulnerables a incidentes tipo `tj-actions/changed-files` (mar-2025), `reviewdog` (sep-2024), `Codecov bash uploader` (2021).
2. Cada `uses:` lleva la versión humana como comentario (`# v4.2.2`) para que dependabot pueda actualizar y para que el revisor sepa qué está aprobando.
3. **Allowlist vacía**. Cualquier excepción debe documentarse aquí y reflejarse en la env var `ALLOWLIST` del job `pin-check` ([workflow-security.yml](.github/workflows/workflow-security.yml)).
4. Workflow `workflow-security.yml` parsea cada `*.yml` con PyYAML y falla el CI si aparece una acción third-party con `@ref` que no sea un SHA de 40 chars hex.

### Permisos

- `permissions: contents: read` a nivel workflow. Los jobs solo escalan a `security-events: write` o `actions: read` cuando es estrictamente necesario (CodeQL).
- `persist-credentials: false` en todos los `actions/checkout` — evita que `GITHUB_TOKEN` quede expuesto a steps posteriores que un atacante podría inyectar.
- `concurrency` con `cancel-in-progress: true` reduce ventana de tokens vivos en runs huérfanos.

### Triggers prohibidos

- ❌ `pull_request_target` — ejecuta con secrets contra código del PR. Vector de ataque #1 en GitHub Actions.
- ❌ `workflow_run` con código mutable del repo origen.
- ✅ Solo `push` (main), `pull_request`, `schedule`, `workflow_dispatch`.

### Detecciones automáticas

| Capa | Herramienta | Detecta |
| --- | --- | --- |
| SAST | CodeQL `security-extended` + `security-and-quality` | command injection, path traversal, deserialización insegura, eval, subprocess inseguro |
| Secretos (filesystem) | `detect-secrets==1.5.0` | API keys, tokens, passwords en código |
| Secretos (historial) | `detect-secrets` sobre últimos 50 commits | secretos commiteados y luego borrados |
| Trojan Source | regex sobre Unicode bidi (CVE-2021-42574) | caracteres `U+202A..U+202E`, `U+2066..U+2069`, `U+200F`, `U+061C` |
| Homoglyphs | regex sobre zero-width | `U+200B`, `U+200C`, `U+200D`, `U+FEFF` que esconden identificadores |
| Ofuscación | grep | `exec(base64...)`, `eval()` dinámico, `os.system()` con `+`, `subprocess(shell=True)` con interpolación, `pickle.loads`, `__import__` dinámico |
| Exfiltración | grep | webhooks Discord/Slack/webhook.site/requestbin/ngrok/pastebin hardcodeados |
| Deps Python | `pip-audit==2.7.3` | CVEs en `pyproject.toml`/`uv.lock` (soft en PR, hard en main/schedule) |
| Workflows mismos | `actionlint` (checksum verificado) + `zizmor==1.5.2` | template injection en `${{ }}`, permisos excesivos, `pull_request_target` peligroso, acciones unpinned |

### SHAs pinned actualmente

```
actions/checkout                      11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
actions/setup-python                  a26af69be951a213d495a4c3e4e4022e16d87065  # v5.4.0
github/codeql-action/init             5c8a8a642e79153f5d047b10ec1cba1d1cc65699  # v3.28.10
github/codeql-action/analyze          5c8a8a642e79153f5d047b10ec1cba1d1cc65699  # v3.28.10
astral-sh/setup-uv                    caf0cab7a618c569241d31dcd442f54681755d39  # v3.2.4
```

### Si ves algo raro en un PR

- Cualquier cambio en `.github/workflows/**` tiene CI dedicado (`workflow-security.yml`). Revisar la salida de zizmor antes de mergear.
- Un PR que añade `uses:` sin SHA: rechazar y referir a esta política.
- Un PR que añade `pull_request_target` o `workflow_run`: rechazar salvo discusión previa.

## Reconocimientos

Reportes válidos serán reconocidos en `CHANGELOG.md` (a menos que el autor pida anonimato).
