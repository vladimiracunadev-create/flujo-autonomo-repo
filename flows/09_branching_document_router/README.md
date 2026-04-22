# 09 Branching Document Router

**Familia:** documentos.

Demuestra branching real: si hay archivos, clasifica y resume; si no hay archivos, escribe un reporte vacío distinto.

## Cuándo Usarlo

- validar `transitions`;
- separar rutas por condición;
- modelar pipelines documentales simples.

## Contexto

```json
{"source_path": "data/dropbox/inbox"}
```

## Salida

- `branching_processed_*.json` cuando hay archivos;
- `branching_empty_*.json` cuando no hay archivos;
- ruta seguida en el estado de la corrida.

## Riesgos

Lee previews de documentos de texto compatibles.

## Ejecución

```bash
python -m engine.runner run flows/09_branching_document_router
```
