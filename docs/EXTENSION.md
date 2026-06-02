# 🧩 Extender Con Acciones De Terceros

> Publica tus propias acciones en un paquete pip y aparecerán en el registro automáticamente.

![Extension](assets/cover-automa-pc.svg)

`LazyActionRegistry` descubre acciones publicadas como entry-points en el grupo `automa.actions`. Cualquier paquete instalado en el mismo entorno puede aportar acciones nuevas sin tocar este repo.

## Estructura de un paquete externo

```text
mi-flujo-extension/
  pyproject.toml
  mi_flujo_extension/
    __init__.py
    actions.py
```

`mi_flujo_extension/actions.py`:

```python
def calcular_iva(amount: float, rate: float = 0.21) -> dict:
    return {"amount": amount, "rate": rate, "iva": round(amount * rate, 2)}
```

`pyproject.toml`:

```toml
[project]
name = "mi-flujo-extension"
version = "0.1.0"
dependencies = []

[project.entry-points."automa.actions"]
"finanzas.calcular_iva" = "mi_flujo_extension.actions:calcular_iva"
```

## Instalación y uso

```bash
uv pip install ./mi-flujo-extension
# o
pip install ./mi-flujo-extension
```

Tras instalar, la acción aparece en el registro:

```bash
automa-validate
# {"ok": true, "registered_actions": 28, ...}
```

Y puede usarse en un manifest:

```json
{
  "id": "calculo_iva",
  "name": "Cálculo IVA",
  "steps": [
    {
      "id": "calc",
      "action": "finanzas.calcular_iva",
      "params": {"amount": 100.0, "rate": 0.19},
      "save_as": "iva"
    }
  ]
}
```

## Buenas prácticas

- **Nombres con namespace**: usa `<dominio>.<verbo>` (`finanzas.calcular_iva`) para no chocar con built-ins.
- **Devuelve `dict`**: las acciones siempre devuelven un dict serializable a JSON; el motor lo guarda en contexto.
- **Falla con excepciones**: una acción que falla debe `raise` con un mensaje claro; el motor maneja retries.
- **No hagas IO no declarado**: si tu acción escribe archivos o hace HTTP, documéntalo. Los manifests confiables pueden restringirla con `allowed_paths`.
- **Tests**: incluye tu propia suite pytest con la acción aislada.
- **Versiona y publica**: si vas a compartirla, súbela a PyPI o a un registry interno.

## Inspección programática

```python
from engine.action_registry import ACTION_REGISTRY
for name in sorted(ACTION_REGISTRY.keys()):
    print(name)
```

`keys()` fuerza la carga lazy de entry-points. La primera invocación es ligeramente más lenta porque hace `importlib.metadata.entry_points`.

## Acciones inline (para tests)

Para tests o scripts ad-hoc puedes registrar callables sin pasar por entry-points:

```python
from engine.action_registry import ACTION_REGISTRY

def fake(**kwargs):
    return {"ok": True, "received": kwargs}

ACTION_REGISTRY.register_callable("test.fake", fake)
```

No se persiste — es sólo para el proceso actual.
