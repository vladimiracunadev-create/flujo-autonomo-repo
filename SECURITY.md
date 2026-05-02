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

## Reconocimientos

Reportes válidos serán reconocidos en `CHANGELOG.md` (a menos que el autor pida anonimato).
