# 04 Document Drop Pipeline

**Familia:** documentos.

Escanea un buzón documental, clasifica archivos por extensión y resume archivos de texto compatibles.

## Cuándo Usarlo

- procesar una carpeta de entrada documental;
- revisar archivos `.txt`, `.md`, `.log`, `.csv` o `.json`;
- generar un reporte legible de un dropbox local.

## Contexto

```json
{"dropbox_path": "data/dropbox/inbox"}
```

## Salida

- inventario de archivos;
- estadísticas por extensión;
- previews de documentos de texto;
- reporte JSON en `output/reports/`.

## Riesgos

Lee contenido textual hasta el límite configurado. Evita apuntarlo a carpetas con información sensible si no necesitas registrar previews.

## Ejecución

```bash
python -m engine.runner run flows/04_document_drop_pipeline
```
