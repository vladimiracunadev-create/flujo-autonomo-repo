# 08 UI Macro Recovery

**Familia:** escritorio.

Ejecuta una hotkey de recuperación, espera y captura evidencia posterior.

## Cuándo Usarlo

- probar acciones de UI;
- ensayar una recuperación simple;
- dejar evidencia visual después de una intervención.

## Contexto

El manifest usa `esc` como hotkey mínima.

## Salida

- resultado de hotkey;
- captura posterior;
- reporte JSON.

## Riesgos

Puede enviar teclas reales al escritorio. Usa una sesión controlada y adapta el flow si necesitas `dry_run`.

## Ejecución

```bash
python -m engine.runner run flows/08_ui_macro_recovery
```
