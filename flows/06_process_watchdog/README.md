# ⚙️ 06 · Watchdog de procesos

> Top de procesos por memoria y alertas si pasan umbrales de CPU o RAM.

| | |
| --- | --- |
| **Familia** | sistema |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS · 🟢 headless |
| **Internet** | ❌ no requerido |
| **Modifica el sistema** | ❌ solo lista procesos (no los mata) |

---

## 🎯 Para qué sirve

- 🧯 Detectar procesos que escalan en memoria o CPU.
- 🔍 Diagnosticar al vuelo qué tiene ocupado el PC.
- 📋 Trazas auditables de uso de procesos.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `top_processes` | `system.top_processes` | `psutil.process_iter`, RSS en MB, ordena por memoria, top 10. Skip silencioso de procesos protegidos. |
| 2 | `watch_processes` | `system.watch_processes` | Para cada proceso del top: si `memory_mb >= 150` o `cpu_percent >= 70` → marca alerta con `reasons`. |
| 3 | `write_report` | `filesystem.write_json` | Reporte con `top` y `watch.alerts`. |

## ⚙️ Configuración

`context.example.json` vacío. Umbrales en manifest:

```json
{"limit": 10, "sort_by": "memory"}                          // top
{"memory_mb_threshold": 150, "cpu_percent_threshold": 70}  // watch
```

## 📋 Requisitos

- ✅ Python 3.10+ y `psutil`.
- ⚠️ En Windows, algunos procesos del sistema requieren admin para inspección completa — el flow los salta sin error.

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["system.top_processes", "system.watch_processes", "filesystem.write_json"],
  "allowed_paths": ["output/reports"]
}
```

## ⚠️ Limitaciones

- ❌ No mata procesos, solo los reporta.
- ❌ `cpu_percent` por `psutil.process_iter` es 0.0 en primera lectura — para valores reales necesitarías muestreo doble.
- ⚠️ Listado puede no ser exhaustivo sin admin en Windows.

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Cuántos procesos | `limit` en manifest |
| Criterio de orden | `sort_by`: `memory` o `cpu` |
| Umbral de RAM | `memory_mb_threshold` |
| Umbral de CPU | `cpu_percent_threshold` |

## 📤 Salidas

- 📊 `output/reports/process_watchdog_<ts>.json` con `top.processes`, `watch.alerts`, `watch.thresholds`.

## ⚡ Ejecución

```bash
flujo run flows/06_process_watchdog
# Programar cada 5 min: */5 * * * *
```
