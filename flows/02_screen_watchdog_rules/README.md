# 👁️ 02 · Watchdog visual por reglas

> Captura pantalla, la analiza y aplica reglas declarativas para clasificar el estado visual.

| | |
| --- | --- |
| **Familia** | pantalla |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS (con sesión gráfica) |
| **Internet** | ❌ no requerido |
| **Modifica el sistema** | ❌ solo escribe en `output/` |

---

## 🎯 Para qué sirve

- 🚨 Generar alertas cuando la pantalla está en un estado anómalo.
- 🤖 Tomar decisiones declarativas sobre la imagen sin tocar UI.
- 📋 Evidencia auditable: cada decisión queda con la regla que matcheó.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `capture_screen` | `screen.capture_screenshot` | Captura monitor primario. Reintenta 1. |
| 2 | `analyze_capture` | `vision.analyze_image` (mock) | Examina luminosidad agregada y devuelve `visual_state ∈ {oscuro, claro, ...}`. |
| 3 | `evaluate_visual_rules` | `rules.evaluate` | Aplica reglas en orden: primera que matchea gana. |
| 4 | `write_report` | `filesystem.write_json` | Reporte con captura, análisis y decisión. |

## ⚙️ Configuración

`context.example.json` solo tiene una nota — las reglas viven en el manifest:

```json
[
  {"id": "pantalla_oscura", "path": "analysis.visual_state", "operator": "eq", "value": "oscuro", "status": "alerta"},
  {"id": "pantalla_clara",  "path": "analysis.visual_state", "operator": "eq", "value": "claro",  "status": "ok"}
]
```

`default_status = "estable"` cuando ninguna regla matchea.

## 📋 Requisitos

- ✅ Python 3.10+, `Pillow`, `mss`. Sesión gráfica activa.
- ❌ NO requiere Tesseract ni proveedores externos.

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["screen.capture_screenshot", "vision.analyze_image", "rules.evaluate", "filesystem.write_json"],
  "allowed_paths": ["output/screenshots", "output/reports"]
}
```

## ⚠️ Limitaciones

- ❌ El analyzer `mock` es heurístico simple, no entiende contenido.
- ❌ Para detectar texto específico usa el flow 10 (OCR + click).
- ⚠️ Las reglas viven en el manifest. Para variar umbrales, copia y edita el flow.

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Reglas y estados | Editar `flows/02_screen_watchdog_rules/manifest.json` |
| Default cuando no hay match | Cambiar `default_status` en el manifest |
| Acción posterior a alerta | Añadir paso `notify.send` con `when` sobre `decision.status` |

## 📤 Salidas

- 🖼️ `output/screenshots/watchdog_<ts>.png`
- 📊 `output/reports/screen_watchdog_<ts>.json`

## ⚡ Ejecución

```bash
flujo run flows/02_screen_watchdog_rules
# Programar cada 5 min: */5 * * * *
```
