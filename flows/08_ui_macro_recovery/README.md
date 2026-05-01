# 🖱️ 08 · Macro de recuperación de UI

> Envía una hotkey (por defecto `Esc`), espera y captura evidencia posterior.

| | |
| --- | --- |
| **Familia** | escritorio |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS (con sesión interactiva) |
| **Internet** | ❌ no requerido |
| **Modifica el sistema** | ⚠️⚠️ **envía teclas reales al escritorio activo** |

---

> [!WARNING]
> Esta acción envía pulsaciones reales de teclado al **proceso/ventana que tenga foco**. Si tu sesión tiene foco en un editor sin guardar o un dashboard sensible, la tecla afecta ahí. **No correr en producción sin saber qué tendrá foco**.

## 🎯 Para qué sirve

- 🆘 Cerrar diálogos modales que bloquean una automatización.
- 🔄 Plantilla mínima para macros de recuperación más complejas.
- 🧪 Validar que `pyautogui` funciona antes del flow 10/11.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `send_recovery_hotkey` | `ui.hotkey` | Envía `["esc"]` con `pyautogui.hotkey`. |
| 2 | `wait_after_hotkey` | `system.wait_seconds` | Espera 1s. |
| 3 | `capture_after_recovery` | `screen.capture_screenshot` | Captura post-acción. Reintenta 1. |
| 4 | `write_report` | `filesystem.write_json` | Reporte. |

## ⚙️ Configuración

La hotkey vive en el manifest:

```json
{"keys": ["esc"]}
```

Ejemplos válidos:

```json
{"keys": ["ctrl", "shift", "esc"]}   // Task Manager (Windows)
{"keys": ["alt", "f4"]}              // Cierra ventana — peligroso
{"keys": ["f5"]}                     // Refresh
{"keys": ["enter"]}                  // Confirma diálogo
```

## 📋 Requisitos

- ✅ Python 3.10+ y `pyautogui`.
- ✅ **Sesión gráfica activa con foco controlable**.
- ⚠️ Linux: `pyautogui` requiere `python3-tk` y servidor X. Wayland es errático.
- ⚠️ macOS: requiere permisos de "Accesibilidad" para Python.

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["ui.hotkey", "system.wait_seconds", "screen.capture_screenshot", "filesystem.write_json"],
  "allowed_paths": ["output/screenshots", "output/reports"],
  "max_runtime_seconds": 15
}
```

## ⚠️ Limitaciones

- ❌ Este flow no tiene `dry_run` por defecto. Para probar, edita el manifest agregando `"dry_run": true` en `params`.
- ❌ `pyautogui` no asegura qué ventana tiene foco — responsabilidad del operador.
- ❌ No hay manera de "deshacer" la hotkey enviada.

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Hotkey | `params.keys` en manifest |
| Espera tras hotkey | `params.seconds` paso 2 |
| Modo seguro | Añadir `"dry_run": true` a params del paso 1 |

## 📤 Salidas

- 🖼️ `output/screenshots/recovery_<ts>.png`
- 📊 `output/reports/ui_macro_recovery_<ts>.json`

## ⚡ Ejecución

```bash
# Recomendado: primero validar con dry_run
flujo run flows/08_ui_macro_recovery
```
