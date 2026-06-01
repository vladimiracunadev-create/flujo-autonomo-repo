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

### Por qué este CI tiene exigencias más altas que la media

El motor de este repo ejecuta acciones reales sobre el escritorio Windows del operador: clicks de mouse, hotkeys, escritura de teclado, capturas de pantalla, lanzamiento de procesos, navegación con Playwright en modo visible. Eso significa que **un commit malicioso fusionado a `main` se convierte en RCE local en cuanto el operador hace `git pull` y ejecuta cualquier flow** — sin necesidad de explotar nada más.

La cadena de daño realista es así:

```
PR malicioso → review distraída → merge a main → git pull en máquina operador
            → ejecución de flow → keylogger / exfil / shell con permisos del usuario
```

Por eso el CI no es solo "tests verdes". Es una **frontera de confianza**: si dejamos que un actor externo influya en lo que termina en `main`, las defensas declarativas del motor (`allowed_actions`, `allowed_paths`, `SandboxPolicy`) sirven de poco — el atacante simplemente las edita en el mismo PR.

### Modelo de amenaza específico

| Escenario | Vector | Mitigación principal |
| --- | --- | --- |
| Acción de GitHub comprometida (tag movido a un commit malicioso) | `uses: foo/bar@v1` empieza a apuntar a payload | Pin a SHA + `pin-check` |
| PR que añade workflow con `pull_request_target` | atacante obtiene secrets + escribe a main | Política explícita + zizmor |
| PR que inyecta payload en `run:` vía `${{ github.event.X }}` | título/branch/comentario controlado por atacante ejecuta shell | zizmor template-injection |
| Dependencia Python comprometida con CVE conocida | `pip install` jala código malicioso | pip-audit en PR + dependabot |
| Secreto commiteado (incluso revertido después) | API key queda en historial git | detect-secrets sobre últimos 50 commits |
| Trojan Source / homoglyph en review | código se ve A pero ejecuta B | regex bidi/zero-width |
| Backdoor con `exec(base64...)` o `pickle.loads` | obfuscación que pasa code review humana | grep de patrones conocidos |
| Exfiltración a webhook externo | Discord/Slack/ngrok hardcodeados en código | grep de dominios C2 típicos |
| Token de CI robado por step posterior comprometido | `GITHUB_TOKEN` en `.git/config` después del checkout | `persist-credentials: false` |
| Permisos excesivos del job | `GITHUB_TOKEN` con `contents: write` por default | `permissions: contents: read` explícito |

### Las 11 capas de defensa: qué, cómo, por qué, qué garantiza, qué no

Cada capa responde a las cuatro preguntas: **qué amenaza para**, **cómo está implementada**, **por qué este enfoque y no otro**, **qué garantiza y qué no**.

#### Capa 1 — Pin a commit SHA en toda acción third-party

- **Para qué.** Cierra la clase de ataque "tag movible" donde el atacante toma control de un repo de acciones (o un mantenedor abusa de su acceso) y mueve `v1`/`main` a un commit con payload. Casos reales: `tj-actions/changed-files` (mar-2025, leak de secrets en miles de repos), `reviewdog/action-setup` (sep-2024), `Codecov bash uploader` (2021).
- **Cómo.** Cada `uses:` apunta a un commit SHA de 40 chars hex con la versión humana en comentario:
  ```yaml
  uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
  ```
- **Por qué SHA y no tag.** Los tags en git son punteros mutables: el dueño del repo puede mover `v4` a otro commit. Un commit SHA es inmutable por construcción (cambiarlo cambia el hash). Dependabot puede seguir actualizando: detecta el comentario `# v4.2.2`, busca un release nuevo y propone un PR con el SHA del release nuevo.
- **Garantiza.** Que el código que GitHub Actions descarga y ejecuta es **exactamente** el que el revisor aprobó al mergear el PR de pinning/upgrade. Si upstream se compromete después, este repo no se ve afectado hasta que un PR explícito cambie el SHA.
- **No garantiza.** Que el SHA original fuera benigno (revisar changelog upstream al mergear PRs de dependabot). Tampoco protege contra un compromiso del propio GitHub.

#### Capa 2 — `pin-check` con parser YAML real

- **Para qué.** Garantizar que la regla de la capa 1 no se rompe por error humano o por un PR adversarial.
- **Cómo.** El job `pin-check` en [workflow-security.yml](.github/workflows/workflow-security.yml) usa Python + PyYAML para parsear cada `*.yml` como AST, recorrer recursivamente buscando claves `uses:` y verificar que el `@ref` matchee `^[0-9a-f]{40}$`. Falla el CI con `::error` si encuentra cualquier excepción no allowlisteada.
- **Por qué parser y no grep.** Un `grep -rn 'uses:'` matchea texto literal dentro de bloques `run:`, comentarios, strings de ejemplo en docs — falsos positivos garantizados. Un parser YAML solo ve **claves YAML reales**, así que es imposible burlar el chequeo escondiendo `uses:` en una cadena.
- **Garantiza.** Que ningún PR puede introducir `uses: foo/bar@main` o `@v3` sin disparar fallo de CI explícito y bloqueante.
- **No garantiza.** Que el SHA pineado sea el que el upstream dice ser (eso es responsabilidad del revisor humano del PR de update).

#### Capa 3 — Allowlist vacía + excepciones documentadas

- **Para qué.** Evitar que "esta acción es de confianza" se convierta en una puerta abierta no auditable.
- **Cómo.** La env var `ALLOWLIST` del job `pin-check` está vacía. Si en el futuro hace falta una excepción (vendor first-party muy reciente sin SHA estable), se agrega ahí **y** en esta sección con justificación.
- **Por qué cero por defecto.** "Allowlists que crecen" es un anti-patrón clásico: lo que entra como excepción temporal se vuelve permanente. Forzar que cada excepción tenga PR + entrada en SECURITY.md crea fricción suficiente para que las personas pinen en lugar de excepcionar.
- **Garantiza.** Que el conjunto de acciones no-pineadas es siempre auditable leyendo este archivo.

#### Capa 4 — `persist-credentials: false` en todos los checkouts

- **Para qué.** Evitar que el `GITHUB_TOKEN` que `actions/checkout` usa para clonar quede grabado en `.git/config` del workspace y disponible para steps posteriores.
- **Cómo.** Todos los `actions/checkout` llevan:
  ```yaml
  with:
    persist-credentials: false
  ```
- **Por qué.** El default de checkout (`persist-credentials: true`) deja el token en `.git/config` para que steps posteriores puedan hacer `git push`. Si **cualquier** step posterior es comprometido (acción third-party con vulnerabilidad, `run:` con injection), puede leer ese archivo y exfiltrar el token. Como ningún job de este repo necesita push desde CI, no hay razón para dejarlo.
- **Garantiza.** Que un step comprometido en un job no puede usar el token para empujar código a `main`. La superficie de daño queda limitada al sandbox del runner.
- **No garantiza.** Protección contra una acción comprometida que reciba el token como input explícito (no se hace en este repo).

#### Capa 5 — Permisos mínimos (`contents: read`)

- **Para qué.** Reducir el alcance del `GITHUB_TOKEN` al mínimo necesario para cada workflow.
- **Cómo.** Cada workflow declara `permissions: contents: read` a nivel top, y solo CodeQL eleva a `security-events: write` + `actions: read` (necesario para subir SARIF).
- **Por qué.** El default de GitHub para repos sin política explícita es `contents: write` + `packages: write`. Un token con `contents: write` puede sobreescribir `main`. Aplicar el principio de mínimo privilegio reduce el blast radius si cualquier capa anterior falla.
- **Garantiza.** Que un step comprometido no puede empujar código, crear releases, ni borrar branches — solo leer.

#### Capa 6 — `concurrency` con `cancel-in-progress`

- **Para qué.** Reducir el tiempo durante el cual hay tokens activos en runners.
- **Cómo.** Cada workflow tiene `concurrency: { group: <wf>-${{ github.ref }}, cancel-in-progress: true }`.
- **Por qué.** Sin esto, varios pushes seguidos al mismo branch arrancan runs paralelas que comparten ventana temporal de tokens. Con cancel, solo la última corre — menos tokens vivos = menos superficie temporal.
- **Garantiza.** Reducción de ventana, no eliminación. No es una defensa fuerte: es higiene.

#### Capa 7 — Triggers prohibidos: `pull_request_target` y `workflow_run`

- **Para qué.** Cerrar el vector de ataque #1 históricamente en GitHub Actions.
- **Cómo.** Por política. Ningún workflow del repo los usa. Cualquier PR que los introduzca debe ser rechazado.
- **Por qué.** `pull_request_target` ejecuta con los **secrets del repo destino** y el **código del PR atacante**. Si combinás eso con un step que confía en `${{ github.event.pull_request.title }}`, cualquiera que abra un PR puede ejecutar shell con tus secrets. `workflow_run` tiene problemas análogos.
- **Garantiza.** Mientras la política se respete (capa 9 lo verifica), un PR de un fork no puede ejecutar código privilegiado.

#### Capa 8 — CodeQL `security-extended` + `security-and-quality`

- **Para qué.** Análisis estático profundo del código Python del repo.
- **Cómo.** Job `codeql` en [security.yml](.github/workflows/security.yml) con `queries: security-extended,security-and-quality`. Genera SARIF que GitHub muestra en la pestaña Security del repo.
- **Por qué queries extendidas.** El set default de CodeQL es conservador (poca señal, poco ruido). El set `security-extended` agrega detectores para command injection, path traversal, deserialización insegura, uso peligroso de `eval`/`exec`/`subprocess`, SSRF — todo lo que importa en un orquestador que ejecuta acciones del sistema. `security-and-quality` agrega anti-patrones que aunque no sean RCE directos crean superficies (e.g. logging de secretos).
- **Garantiza.** Detección de la mayoría de patrones documentados de CWE Top 25 sobre Python.
- **No garantiza.** Detección de bugs lógicos del dominio (e.g. una validación de path que se puede bypassear con un input que CodeQL no modela). Tampoco vulnerabilidades en dependencias (eso es pip-audit).

#### Capa 9 — `actionlint` + `zizmor` sobre los propios workflows

- **Para qué.** Aplicar SAST al **código de CI** mismo, no solo al código de aplicación.
- **Cómo.** Job en [workflow-security.yml](.github/workflows/workflow-security.yml):
  - `actionlint 1.7.7` (descargado con verificación de checksum SHA256) → sintaxis + reglas de seguridad estándar.
  - `zizmor==1.5.2` con `--persona=auditor` → analizador especializado en GitHub Actions:
    - **template-injection**: detecta `${{ github.event.X }}` interpolado dentro de `run:` (donde X es controlable por atacante).
    - **excessive-permissions**: workflows con permisos más amplios de lo necesario.
    - **dangerous-triggers**: `pull_request_target` / `workflow_run` mal usados.
    - **unpinned-uses**: tags en lugar de SHA (redundancia con capa 2).
    - **artipacked / cache-poisoning**: artifacts y cache mal manejados.
- **Por qué dos herramientas.** actionlint cubre sintaxis y reglas conservadoras; zizmor es más reciente y especializado en clases de ataque modernas. Ningún linter solo cubre todo.
- **Garantiza.** Que ningún workflow puede hacer `run: echo "${{ github.event.pull_request.title }}"` (typical injection) sin disparar fallo de CI.
- **No garantiza.** Bugs lógicos de tu CI (e.g. un script Python custom dentro de `run:` con su propio sink injection — eso lo cubre CodeQL si está en `engine/`).

#### Capa 10 — `detect-secrets` sobre filesystem + historial

- **Para qué.** Asegurar que no hay credenciales en el código ni en el historial.
- **Cómo.** Job `detect-secrets` en [security.yml](.github/workflows/security.yml):
  1. Versión pineada `detect-secrets==1.5.0` (no `latest` — un atacante con acceso al PyPI no puede inyectar firmas falsas en una versión vieja).
  2. Escaneo del filesystem actual con baseline.
  3. **Escaneo de los últimos 50 commits**: para cada commit hace `git checkout` del árbol completo a `/tmp` y corre detect-secrets sobre ese snapshot. Detecta secretos que fueron commiteados y borrados después (clásico "ups, lo revertí — pero sigue en el historial").
- **Por qué historial completo de 50 commits y no solo HEAD.** Un secret borrado del HEAD pero presente en cualquier commit accesible vía `git log` ya es público y debe rotarse. El escaneo de HEAD solamente da falsa sensación de seguridad.
- **Garantiza.** Detección de patrones conocidos (API keys de AWS/Stripe/Slack/GitHub, JWT, claves privadas RSA/ED25519, etc.) con muy bajo falso negativo en los formatos canónicos.
- **No garantiza.** Detección de secretos en formatos custom (string opaco que solo tu sistema sabe interpretar como credencial). Para esos, se usa `.secrets.baseline` con allowlist explícito y un humano revisa.

#### Capa 11 — Trojan Source, ofuscación, exfiltración

- **Para qué.** Detectar payloads que pasarían review humana porque "el código se ve bien".
- **Cómo.** Job `supply-chain` en [security.yml](.github/workflows/security.yml) usa `git ls-files | xargs grep -P` para buscar:

  | Detección | Patrón | Por qué importa |
  | --- | --- | --- |
  | Trojan Source (CVE-2021-42574) | `U+202A..E`, `U+2066..9`, `U+200F`, `U+061C` | Caracteres bidi reordenan visualmente el código: lo que ves en el editor no es lo que el compilador ejecuta |
  | Zero-width / homoglyphs | `U+200B/C/D`, `U+FEFF` | Crean identificadores visualmente idénticos pero distintos para el parser (`admin` vs `adm​in`) |
  | base64 + exec | `exec(base64.b64decode(...))` | Patrón clásico de dropper: payload codificado para evadir grep simple |
  | eval dinámico | `eval(<expr no literal>)` | RCE si el argumento viene de input externo |
  | os.system con concat | `os.system(... + ...)` | Command injection clásico |
  | subprocess shell=True interpolado | `subprocess.X(... shell=True ... f"" / + / .format())` | Command injection en disfraz |
  | pickle.loads | `pickle.loads(...)` | Deserialización insegura = RCE si el dato no es local |
  | `__import__` dinámico | `__import__(<no literal>)` | Carga de módulos arbitrarios |
  | Webhooks de exfil hardcodeados | discord.com/api/webhooks, hooks.slack.com, webhook.site, requestbin, burpcollaborator, ngrok.io, pastebin.com/raw | Lista de servicios típicamente usados como C2 / exfil |

- **Por qué grep y no SAST puro.** Estos patrones son **textuales**: bidi unicode no es un AST, una URL hardcodeada es una string. CodeQL puede detectar algunos pero el grep es más rápido, más fácil de auditar y permite una lista explícita de IOCs (indicadores de compromiso).
- **Por qué fallar el CI ante warning.** Un `eval()` dinámico legítimo es raro y debe documentarse explícitamente. Mejor falsos positivos que se silencian con allowlist que falsos negativos silenciosos.
- **Garantiza.** Que un PR no puede mergear con bidi unicode visible, ni con un dropper base64+exec evidente, ni con una URL de exfil de los servicios listados.
- **No garantiza.** Detección de payloads ofuscados con técnicas no listadas (e.g. cifrado custom, dominio C2 propio, ROT13). Para eso es la review humana.

#### Capa 12 — `pip-audit` con enforcement progresivo

- **Para qué.** Detectar vulnerabilidades conocidas en dependencias Python.
- **Cómo.** Job `pip-audit` en [security.yml](.github/workflows/security.yml):
  - `pip-audit==2.7.3` pineado.
  - **Soft mode** en pull requests: avisa pero no bloquea (permite mergear cuando la fix aún no salió upstream pero el riesgo es aceptable).
  - **Hard mode** en push a `main` y schedule semanal: falla CI.
- **Por qué progresivo.** Bloquear todo PR por una CVE en una dep transitiva sin fix paraliza el desarrollo. Pero permitir que `main` quede con CVEs en hard sí es inaceptable. La asimetría refleja que `main` es la frontera de confianza, no PRs en flight.
- **Garantiza.** Que `main` no tiene dependencias con CVEs publicadas en la base de PyPA Advisory.
- **No garantiza.** Vulnerabilidades 0-day o no reportadas todavía. Tampoco backdoors deliberados en deps (eso requiere análisis de comportamiento, fuera de alcance de este repo).

### SHAs activos

```
actions/checkout                      11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
actions/setup-python                  a26af69be951a213d495a4c3e4e4022e16d87065  # v5.4.0
github/codeql-action/init             7211b7c8077ea37d8641b6271f6a365a22a5fbfa  # v4.36.0
github/codeql-action/analyze          7211b7c8077ea37d8641b6271f6a365a22a5fbfa  # v4.36.0
astral-sh/setup-uv                    caf0cab7a618c569241d31dcd442f54681755d39  # v3.2.4
```

Versiones pineadas de herramientas (no acciones, sino binarios/paquetes que el CI descarga):

```
detect-secrets                        1.5.0
pip-audit                             2.7.3
zizmor                                1.5.2
actionlint                            1.7.7  (con verificación de checksum SHA256)
pyyaml                                6.0.2
```

### Lo que este hardening NO resuelve

Honestidad: estas capas no son una caja fuerte completa. Específicamente **no protegen contra**:

- **Compromiso de la cuenta del mantenedor** (alguien con acceso a `main` puede mergear lo que quiera). Mitigación: 2FA obligatorio + branch protection.
- **Compromiso de GitHub mismo** (incidente de plataforma). Sin mitigación a nivel repo.
- **Backdoor en dependencia upstream pineada antes de que se publique CVE**. Mitigación parcial: pip-audit detecta cuando se publica el CVE, pero hay ventana de vulnerabilidad.
- **Compromiso del runner de GitHub** (ataques contra la VM de Actions). Mitigación: permisos mínimos limitan blast radius.
- **Errores semánticos en el motor** (e.g. un bug en `engine/sandbox.py` que permite bypass). Mitigación: tests + code review humana, no CI.
- **Manifests externos maliciosos**. Esa es la frontera del usuario, no del CI — ver [docs/SEGURIDAD.md](docs/SEGURIDAD.md) §"Modelo De Confianza".

### Procedimiento de revisión de PRs

Cuando llega un PR, el revisor debe verificar (en orden):

1. CI completo en verde — incluyendo `workflow-security.yml`.
2. Cualquier cambio en `.github/workflows/**` recibe atención especial: leer la salida de zizmor en el log del run, no solo confiar en el ✅.
3. Cualquier `uses:` nuevo: verificar manualmente que el SHA propuesto existe en el repo upstream y corresponde al tag declarado en el comentario.
4. Cualquier dep nueva en `pyproject.toml`: verificar que no aparece en el log de pip-audit como vulnerable.
5. PRs que toquen `engine/sandbox.py`, `engine/secrets.py`, `app/server.py`: review humana detallada — el CI no detecta bypasses lógicos.

Si zizmor o `pin-check` fallan, **no mergear** aunque el resto esté verde. La política es bloqueo duro.

## Reconocimientos

Reportes válidos serán reconocidos en `CHANGELOG.md` (a menos que el autor pida anonimato).
