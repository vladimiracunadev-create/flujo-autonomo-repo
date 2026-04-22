# Familias y casos

## Familias

- pantalla
- escritorio
- navegador
- sistema
- documentos
- filesystem

## Casos incluidos

- `01_screen_capture_analyze` → pantalla
- `02_screen_watchdog_rules` → pantalla
- `03_folder_inventory` → filesystem
- `04_document_drop_pipeline` → documentos
- `05_system_healthcheck` → sistema
- `06_process_watchdog` → sistema
- `07_browser_assisted_capture` → navegador
- `08_ui_macro_recovery` → escritorio
- `09_branching_document_router` → documentos + branching
- `10_screen_ocr_click_recovery` → pantalla + OCR + UI visual

## Regla del repositorio

Solo se crea una carpeta en `flows/` cuando existe un flujo ejecutable real.


## Nuevos casos v5

- **pantalla**
  - `11_screen_tri_mode_operator`: flujo de pantalla con OCR, visión o análisis híbrido.
