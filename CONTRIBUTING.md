# 🤝 Contribuir a Flujo Autónomo

> Antes de contribuir leé el [CHANGELOG.md](CHANGELOG.md) para entender el estado actual y los cambios recientes.

## ⚡ Setup local

```bash
# Con uv (recomendado)
uv sync --extra dev --extra schema

# Para Playwright (caso 02 y 07)
python -m playwright install chromium
```

## ✅ Antes de abrir un PR

Tres cosas que **siempre** deben pasar:

```bash
# 1. Tests
uv run pytest

# 2. Lint
uv run ruff check .

# 3. Validador de manifests + schema
uv run python scripts/validate_project.py
```

Estos también corren en CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) en matriz Linux/Windows × Python 3.10/3.11/3.12.

## 🆕 Crear un flow nuevo

1. Crea `flows/NN_mi_flow/` con `manifest.json`, `context.example.json` y `README.md`.
2. Sigue la **estructura uniforme de README** documentada en [docs/CREAR_FLUJOS.md](docs/CREAR_FLUJOS.md):
   - 🎯 Para qué sirve
   - 🧭 Flujo paso a paso
   - ⚙️ Configuración
   - 📋 Requisitos
   - 🛡️ Sandbox sugerido
   - ⚠️ Limitaciones honestas
   - 🎮 Control que tienes
   - 📤 Salidas
   - ⚡ Ejecución
3. Si la acción no existe, agrégala en `actions/` y regístrala en `engine/action_registry.py`.
4. Si tu flow va al panel: revisa los atajos `Alt+1..Alt+=` en `app/server.py` (`_SHORTCUT_LABELS`).
5. Si tu flow es interactivo (input inline tipo flow 02 / 03 / 07), añade el bloque `inline_input_html` en `_flow_card_run_tab`.

## 🐍 Estilo de código

- Python ≥ 3.10. Usa `dict[str, ...]`, `list[...]`, `X | None` (no `typing.Dict`).
- Imports ordenados por isort (lo aplica `ruff check . --fix`).
- `from __future__ import annotations` cuando uses tipos modernos.
- Docstrings en módulos/funciones públicas.
- Sin comentarios narrando el "qué" del código — comentar solo el "por qué" cuando no sea obvio.

## 🛡️ Cambios que tocan la SandboxPolicy

Cualquier cambio en `engine/sandbox.py` o en cómo el orquestador aplica la política:

- Tests específicos en `tests/test_sandbox.py`.
- Documenta el nuevo comportamiento en `docs/SEGURIDAD.md`.
- Agrega entrada en `CHANGELOG.md` bajo "🛡️ Seguridad".

## 📚 Documentación

Cualquier feature visible al usuario debe actualizar:

- `README.md` — catálogo, badges si aplica.
- `docs/MANUAL_USUARIO.md` — sección del caso afectado.
- `docs/FAMILIAS_Y_CASOS.md` — matriz de compatibilidad si aplica.
- `CHANGELOG.md` — entrada en la versión actual.

## 🐛 Reportar bugs

- Issues en [GitHub Issues](https://github.com/vladimiracunadev-create/flujo-autonomo-repo/issues).
- Vulnerabilidades de seguridad: ver [SECURITY.md](SECURITY.md), **no en issues públicos**.

## 📜 Licencia

Al contribuir aceptas que tu aporte se publique bajo MIT (ver [LICENSE](LICENSE)).
