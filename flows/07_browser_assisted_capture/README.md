# 07 Browser Assisted Capture

**Familia:** navegador.

Abre una página HTML local, espera que cargue, captura pantalla y genera evidencia visual.

## Cuándo Usarlo

- validar interacción navegador + captura;
- documentar una pantalla local;
- probar automatización asistida por navegador sin depender de internet.

## Contexto

Usa `data/web/control_page.html`.

## Salida

- resultado de apertura del archivo;
- captura de pantalla;
- análisis de metadata de imagen;
- reporte JSON.

## Requisitos

- navegador disponible;
- escritorio gráfico;
- permisos de captura.

## Ejecución

```bash
python -m engine.runner run flows/07_browser_assisted_capture
```
