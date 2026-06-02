# 🖥️ Mostrar escritorio y capturar

## 🎯 Para qué sirve

Capturar el **escritorio limpio** (sin ventanas encima) en una sola operación. Útil para:

- Auditar wallpaper / íconos / gadgets en parques de equipos.
- Documentar el estado inicial del escritorio antes/después de una sesión operativa.
- Detectar widgets o íconos inesperados sin tener que minimizar ventanas a mano.

## 🧭 Flujo paso a paso

1. **minimize_all_windows** → `Win+D` minimiza todas las ventanas abiertas.
2. **wait_animation** → espera 800 ms para que la animación de Windows termine y el escritorio quede estable.
3. **capture_desktop** → `mss` captura la pantalla completa a PNG con timestamp.

## ⚙️ Configuración

| Campo | Tipo | Por defecto | Significado |
| --- | --- | --- | --- |
| `dry_run` | bool | `false` | Si `true`, no envía `Win+D` (las ventanas no se minimizan); sí captura. Útil para probar el wiring. |

## 📋 Requisitos

- Sesión Windows interactiva con escritorio gráfico.
- `pyautogui` (hotkey) y `mss` (captura) — ya incluidos.
- Carpeta `output/screenshots/` (se crea sola).

## 🛡️ Sandbox sugerido

```json
"allowed_actions": ["ui.hotkey", "system.wait_seconds", "screen.capture_screenshot"],
"allowed_paths": ["output/screenshots"],
"max_runtime_seconds": 10
```

Aplicado en el manifest.

## ⚠️ Limitaciones honestas

- `Win+D` **restaura** las ventanas si se envía dos veces seguidas — si ejecutas el flow estando en escritorio limpio, las ventanas vuelven. El segundo `Win+D` sí se enviaría en una próxima corrida.
- En multimonitor, captura **la pantalla principal**. Para multimonitor explícito, hay que extender `screen.capture_screenshot` (no es prioritario hoy).
- No mueve ventanas — `Win+D` solo las minimiza. Algunas apps modales pueden ignorarlo.

## 🎮 Control que tienes

- Programable con cron (ej: capturar el escritorio cada hora).
- `dry_run: true` no minimiza pero sí captura — útil para detectar cambios sin interrumpir tu trabajo.

## 📤 Salidas

- **PNG**: `output/screenshots/desktop_clean_<timestamp>.png` con la captura del escritorio.
- **Run en SQLite** con `shot.path` apuntando al PNG.

## ⚡ Ejecución

Desde el panel: tab **Ejecutar** → atajo `Alt+9` o click en la card.

CLI:

```bash
flujo run flows/09_show_desktop_capture
```
