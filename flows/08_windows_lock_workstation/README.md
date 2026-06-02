# 🔒 Bloquear estación de trabajo

## 🎯 Para qué sirve

Bloquear la sesión Windows actual con un clic desde el panel — equivale a `Win+L` desde el teclado.

## 🧭 Flujo paso a paso

1. **send_lock_hotkey** → envía `Win+L` vía `ui.hotkey`. El sistema bloquea inmediatamente.

## ⚙️ Configuración

`context.example.json`:

| Campo | Tipo | Por defecto | Significado |
| --- | --- | --- | --- |
| `dry_run` | bool | `false` | Si `true`, no bloquea — solo registra que se hubiera enviado el atajo. Útil para validar el wiring desde tests. |

## 📋 Requisitos

- Sesión Windows interactiva.
- `pyautogui` instalado (ya viene como dependencia del proyecto).

## 🛡️ Sandbox sugerido

```json
"allowed_actions": ["ui.hotkey"],
"max_runtime_seconds": 5
```

Ya está aplicado en el manifest. El flow no toca filesystem ni red.

## ⚠️ Limitaciones honestas

- Bloquea **inmediatamente** al ejecutar — si tienes trabajo sin guardar, guardalo antes.
- En equipos con políticas corporativas que requieren autenticación adicional al desbloquear, el bloqueo funciona igual pero el desbloqueo seguirá la política del equipo.
- No funciona en sesiones SSH ni Remote Desktop si el cliente no propaga teclas modificadoras de Windows.

## 🎮 Control que tienes

- Programable con cron desde el tab Programadas (ej: bloquear cada noche a las 23:00).
- Disparable por webhook si `AUTOMA_WEBHOOK_TOKEN` está configurado.
- `dry_run: true` permite verificar que el step llega sin bloquear.

## 📤 Salidas

Solo registro en SQLite del run con `lock_result.sent: true`. No produce archivos.

## ⚡ Ejecución

Desde el panel: tab **Ejecutar** → atajo `Alt+8` o click en la card del flow.

CLI:

```bash
flujo run flows/08_windows_lock_workstation
```
