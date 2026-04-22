# 02 Screen Watchdog Rules

**Familia:** pantalla.

Captura pantalla, analiza su estado visual y evalúa reglas declarativas para clasificar el resultado.

## Cuándo Usarlo

- detectar estados visuales básicos;
- validar branching por reglas sin tocar UI;
- generar evidencia de pantalla para auditoría local.

## Contexto

Usa el analizador `mock` por defecto para operar sin IA externa.

## Salida

- captura en `output/screenshots/`;
- reporte con `capture`, `analysis` y `decision`;
- historial de pasos en SQLite.

## Requisitos

- escritorio gráfico si no se adapta a imagen existente;
- permisos de captura.

## Ejecución

```bash
python -m engine.runner run flows/02_screen_watchdog_rules
```
