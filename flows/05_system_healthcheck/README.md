# 🖥️ 05 · Healthcheck del sistema

> Snapshot de CPU/memoria/disco y clasificación por umbrales.

| | |
| --- | --- |
| **Familia** | sistema |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS · 🟢 headless |
| **Internet** | ❌ no requerido |
| **Modifica el sistema** | ❌ solo lee métricas |

---

## 🎯 Para qué sirve

- 🩺 Monitorear salud básica del PC sin agente externo.
- 🚨 Disparar alertas (vía `notify.send`) cuando memoria o CPU pasan umbrales.
- 📈 Acumular series temporales en SQLite para gráfico posterior.
- ⚡ **El flow más rápido del repo (~0.7s)** — bueno para validar el motor.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `take_snapshot` | `system.snapshot_system` | `psutil`: timestamp, plataforma, Python, CPU%, mem%, mem usada (MB), disco%, disco usado (GB). |
| 2 | `evaluate_snapshot` | `rules.evaluate` | mem > 85% → `alerta`. CPU > 90% → `alerta`. Default → `ok`. |
| 3 | `write_snapshot` | `filesystem.write_json` | Snapshot + decisión. |

## ⚙️ Configuración

`context.example.json` está vacío. Reglas en manifest:

```json
[
  {"id": "memoria_alta", "path": "snapshot.memory_percent", "operator": "gt", "value": 85, "status": "alerta"},
  {"id": "cpu_alta",     "path": "snapshot.cpu_percent",    "operator": "gt", "value": 90, "status": "alerta"}
]
```

## 📋 Requisitos

- ✅ Python 3.10+ y `psutil`.
- ❌ NO requiere sesión gráfica ni internet.

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["system.snapshot_system", "rules.evaluate", "filesystem.write_json"],
  "allowed_paths": ["output/reports"],
  "max_runtime_seconds": 10
}
```

## ⚠️ Limitaciones

- ❌ Solo CPU, memoria y disco raíz. Para temperaturas, batería, GPU, extender `actions/system.py`.
- ❌ Snapshot instantáneo, no agrega muestras.
- ⚠️ `cpu_percent` con `interval=0.2` introduce ~200ms (lectura representativa).

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Umbrales de alerta | Editar `value` de las reglas en manifest |
| Métricas extra | Extender `actions/system.py:snapshot_system` |
| Notificar al alertar | Añadir paso `notify.send` con `when` sobre `decision.status` |
| Frecuencia | Scheduler con cron o intervalo |

## 📤 Salidas

- 📊 `output/reports/system_health_<ts>.json`:

```json
{
  "snapshot": {
    "platform": "Windows-11-...", "cpu_percent": 7.5, "memory_percent": 62.4,
    "memory_used_mb": 7905.13, "disk_percent": 78.2, "disk_used_gb": 380.1
  },
  "decision": {"status": "ok", ...}
}
```

## ⚡ Ejecución

```bash
flujo run flows/05_system_healthcheck
# Programar cada 10 min: */10 * * * *
```
