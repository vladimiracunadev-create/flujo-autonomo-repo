# 03 Folder Inventory

**Familia:** filesystem.

Lista una carpeta configurable, calcula estadísticas por extensión y escribe un inventario en JSON.

## Cuándo Usarlo

- revisar contenido de una carpeta;
- generar evidencia simple de archivos;
- probar acciones filesystem sin tocar UI.

## Contexto

```json
{"path_override": "data/inbox"}
```

## Salida

- reporte en `output/reports/folder_inventory_*.json`;
- estadísticas de cantidad, tamaño total, extensiones y archivo mayor.

## Riesgos

Solo lee la carpeta configurada y escribe reporte.

## Ejecución

```bash
python -m engine.runner run flows/03_folder_inventory
```
