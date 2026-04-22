# 06 Process Watchdog

**Familia:** sistema.

Lista procesos principales y marca alertas cuando superan umbrales de CPU o memoria.

## Cuándo Usarlo

- observar procesos pesados;
- diagnosticar consumo local;
- alimentar reportes periódicos de salud.

## Contexto

Los umbrales están declarados en el manifest. Pueden ajustarse creando una variante del flow o editando el manifest con cuidado.

## Salida

- top de procesos;
- alertas por memoria o CPU;
- reporte JSON en `output/reports/`.

## Requisitos

- dependencia `psutil`;
- permisos suficientes para consultar procesos.

## Ejecución

```bash
python -m engine.runner run flows/06_process_watchdog
```
