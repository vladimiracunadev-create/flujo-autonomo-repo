# 01 Screen Capture Analyze

**Familia:** pantalla.

Captura la pantalla actual, ejecuta un analizador local y deja un reporte físico. Es el caso base para comprobar que el entorno puede tomar evidencia visual.

## Cuándo Usarlo

- validar que una aplicación está abierta;
- dejar evidencia visual de una corrida;
- probar `screen.capture_screenshot`;
- preparar casos posteriores con OCR o visión.

## Contexto

`context.example.json` define el analizador por defecto.

## Salida

- captura en `output/screenshots/`;
- reporte JSON en `output/reports/`;
- estado y eventos persistidos por el motor.

## Requisitos

- escritorio gráfico real;
- permisos de captura de pantalla;
- dependencias `mss` o `Pillow`.

## Ejecución

```bash
python -m engine.runner run flows/01_screen_capture_analyze
```
