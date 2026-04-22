# Validación

El repositorio tiene dos niveles de validación: una revisión liviana de estructura y una prueba integral de ejecución.

## Validación Liviana

```bash
python scripts/validate_project.py
```

Comprueba:

- que cada `flows/*/manifest.json` se pueda leer;
- que tenga `id`, `name` y `steps`;
- que no existan pasos duplicados;
- que cada `action` esté registrada;
- que cada transición `next` apunte a un paso existente;
- que `start_step`, si existe, sea válido.

No ejecuta acciones ni escribe en SQLite.

## Listado De Flows

```bash
python -m engine.runner list
```

Debe funcionar incluso sin dependencias opcionales instaladas, porque el registry carga acciones bajo demanda.

## Smoke Test

```bash
python scripts/smoke_test.py
```

Comprueba:

- inicialización de SQLite;
- sincronización de flows;
- configuración guardada;
- ejecución de flows representativos;
- branching documental;
- flow visual tri-modo en modo `mock`;
- scheduler básico;
- consulta posterior de runs.

## Criterios De Aceptación

Antes de subir cambios:

1. `python scripts/validate_project.py` debe terminar con `"ok": true`.
2. `python -m engine.runner list` debe listar los casos.
3. Si se tocaron acciones, motor o manifests, correr `python scripts/smoke_test.py`.
4. Si se tocó documentación, verificar que no queden referencias heredadas a versiones internas.

## Limitaciones De Validación

- El validador no evalúa semántica completa de parámetros.
- El smoke test requiere permisos de escritura en `db/`, `state/`, `logs/` y `output/`.
- Los flows con captura real requieren escritorio gráfico.
- OCR requiere Tesseract instalado fuera de Python.
- Proveedores de visión externos requieren endpoint/modelo/API key válidos.

## Señales De Calidad

Un cambio está bien encaminado cuando:

- mejora trazabilidad sin ocultar errores;
- conserva compatibilidad con manifests existentes;
- evita importar dependencias opcionales para operaciones simples;
- documenta riesgos de acciones con efectos reales;
- deja ejemplos reproducibles.
