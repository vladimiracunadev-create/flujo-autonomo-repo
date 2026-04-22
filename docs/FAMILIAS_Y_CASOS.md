# Familias Y Casos

La documentación usa dos niveles:

- **Familia**: categoría conceptual del problema.
- **Caso**: flow ejecutable con manifest, contexto y README propio.

Solo se crea una carpeta en `flows/` cuando existe un proceso real que el motor puede ejecutar.

## Familias Actuales

| Familia | Uso |
| --- | --- |
| `pantalla` | captura, análisis visual, OCR y decisiones sobre interfaz |
| `escritorio` | interacción directa con UI local |
| `navegador` | apertura de recursos web/locales y captura asistida |
| `sistema` | salud del equipo, procesos y métricas locales |
| `documentos` | entrada documental, resumen y routing |
| `filesystem` | inventario y operaciones sobre archivos/carpetas |

## Catálogo

| Caso | Familia | Entrada principal | Salida esperada |
| --- | --- | --- | --- |
| `01_screen_capture_analyze` | pantalla | pantalla actual | captura y análisis local |
| `02_screen_watchdog_rules` | pantalla | captura visual | reporte con decisión por reglas |
| `03_folder_inventory` | filesystem | `path_override` | inventario y estadísticas |
| `04_document_drop_pipeline` | documentos | `dropbox_path` | resumen documental |
| `05_system_healthcheck` | sistema | equipo local | snapshot y decisión |
| `06_process_watchdog` | sistema | procesos activos | alertas por CPU/memoria |
| `07_browser_assisted_capture` | navegador | HTML local | evidencia visual de navegador |
| `08_ui_macro_recovery` | escritorio | hotkey de recuperación | captura posterior |
| `09_branching_document_router` | documentos | `source_path` | ruta procesada o vacía |
| `10_screen_ocr_click_recovery` | pantalla | texto objetivo | click visual o recuperación |
| `11_screen_tri_mode_operator` | pantalla | imagen/captura y config visual | decisión click/recover y reporte |

## Criterios Para Agregar Un Caso

Un nuevo caso debe:

1. Tener un problema operativo claro.
2. Incluir `manifest.json`.
3. Incluir `context.example.json`.
4. Incluir README del caso con propósito, requisitos y salida.
5. Usar acciones registradas o agregar la acción correspondiente.
6. Pasar `python scripts/validate_project.py`.
7. Evitar efectos destructivos por defecto.

## Nomenclatura

El prefijo numérico ordena los casos para lectura humana. No representa versión del producto. Si un nuevo caso reemplaza a otro, se documenta la relación en el README del caso en lugar de renombrar todo el árbol.
