# 05 System Healthcheck

**Familia:** sistema.

Toma un snapshot del equipo y evalúa reglas simples de CPU y memoria.

## Cuándo Usarlo

- verificar salud básica del equipo;
- probar acciones de sistema;
- generar señal rápida para scheduler.

## Contexto

No requiere configuración especial.

## Salida

- snapshot con plataforma, Python, CPU, memoria y disco;
- decisión `ok` o `alerta`;
- reporte en `output/reports/system_health_*.json`.

## Requisitos

- dependencia `psutil`.

## Ejecución

```bash
python -m engine.runner run flows/05_system_healthcheck
```
