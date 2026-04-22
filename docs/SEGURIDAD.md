# Seguridad Operativa

Flujo Autónomo ejecuta automatizaciones locales. Eso lo hace útil, pero también exige tratar cada manifest como código operativo.

## Modelo De Confianza

El sistema asume que:

- el operador controla el repositorio;
- los manifests vienen de una fuente confiable;
- el panel corre en localhost;
- las acciones se ejecutan con permisos del usuario local.

No asume:

- aislamiento fuerte por acción;
- control multiusuario;
- sandbox de filesystem;
- revisión automática de comandos peligrosos;
- coordinación distribuida.

## Superficies Sensibles

| Superficie | Riesgo | Control actual |
| --- | --- | --- |
| Filesystem | leer, mover o escribir archivos | manifests explícitos, `.gitignore` para salidas |
| UI automation | clicks, hotkeys y escritura | `dry_run` en acciones UI críticas |
| Procesos | ejecución local | `ui.launch_process` usa `shell=false` por defecto |
| Red | requests HTTP | acción explícita `http.fetch_url` |
| Pantalla | captura de información visible | ejecución local y archivos ignorados |
| Visión externa | envío de imágenes a endpoint | proveedor configurable y `mock` por defecto en pruebas |

## Reglas De Uso Seguro

1. Revisa `manifest.json` antes de ejecutar un flow nuevo.
2. Usa `python scripts/validate_project.py` antes de correr.
3. Mantén `ui_dry_run = true` mientras calibras coordenadas.
4. No uses scheduler en flows que todavía no probaste manualmente.
5. No guardes API keys en `configs/`; usa variables de entorno.
6. No apuntes acciones filesystem a carpetas críticas sin backup.
7. Trata `fallback_bbox` como configuración manual, no como detección.

## Acciones Con Mayor Cuidado

- `filesystem.move_file`
- `filesystem.write_json`
- `ui.launch_process`
- `ui.click`
- `ui.click_bbox`
- `ui.hotkey`
- `http.fetch_url`
- `screen.capture_screenshot`

## Buenas Prácticas Para Manifests

- Prefiere rutas dentro del workspace.
- Escribe reportes en `output/reports/`.
- Escribe capturas en `output/screenshots/`.
- Evita `overwrite=true` salvo que esté justificado.
- Incluye transiciones de recuperación para pasos frágiles.
- Usa `max_steps_per_run` si el flow tiene loops.
- Deja contexto de ejemplo sin secretos.

## Datos Sensibles

Los archivos generados pueden contener:

- rutas locales;
- capturas de pantalla;
- texto extraído por OCR;
- nombres de procesos;
- respuestas de servicios externos;
- errores con detalles del entorno.

Por eso `db/*.db`, `logs/*.jsonl`, `state/*.json`, `output/**/*.json` y `output/**/*.png` están ignorados.

## Alcance Actual

Esta primera versión prioriza claridad, trazabilidad y operación local. Para uso multiusuario, integración empresarial o ejecución de manifests no confiables haría falta agregar sandboxing, allowlists por acción, perfiles de permisos y autenticación del panel.
