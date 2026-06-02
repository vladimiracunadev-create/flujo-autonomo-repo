# 📁 Abrir File Explorer en una ruta

## 🎯 Para qué sirve

Atajo de un clic para abrir File Explorer directamente en una carpeta específica. Ahorra el ciclo "abrir Explorer → navegar manualmente al path → ahí estoy".

Casos de uso típicos:

- Carpeta `output/reports/` del propio proyecto al revisar runs.
- Carpeta de descargas o de logs del PC al diagnosticar.
- Cualquier ruta UNC `\\servidor\share` para auditoría rápida.

## 🧭 Flujo paso a paso

1. **launch_explorer** → ejecuta `explorer.exe <folder_path>`.

Una sola acción. El proceso retorna inmediatamente con el PID de Explorer.

## ⚙️ Configuración

| Campo | Tipo | Por defecto | Significado |
| --- | --- | --- | --- |
| `folder_path` | string | `C:\Users` | Ruta de la carpeta a abrir. Puede ser local (`C:\...`), UNC (`\\server\share`) o relativa al CWD. |
| `dry_run` | bool | `false` | Si `true`, no abre ventana; registra el comando que se hubiera ejecutado. |

Para cambiar la carpeta sin tocar este archivo, usa `configs/explorer_open_path.json` o el modal de Configuración del flow en el panel.

## 📋 Requisitos

- Sesión Windows (en Linux/macOS `explorer.exe` no existe — el flow falla limpio con `FileNotFoundError`).
- Permisos de lectura sobre la carpeta destino (si no, Explorer abre y muestra "Acceso denegado").

## 🛡️ Sandbox sugerido

```json
"allowed_actions": ["ui.launch_process"],
"max_runtime_seconds": 5
```

> [!IMPORTANT]
> Este flow **no declara `allowed_paths`** porque `folder_path` es un argumento a un proceso externo, no una ruta donde el motor escriba. El sandbox de paths del motor no aplica a procesos hijos — la verificación corre por cuenta del propio Explorer (permisos NTFS).

## ⚠️ Limitaciones honestas

- Rutas con espacios funcionan vía `shlex.split` siempre que estén entre comillas en `folder_path` (ej: `"C:\\Program Files"`). Si das una ruta sin comillas y con espacios, el split corta mal y Explorer abre en una ruta inesperada.
- `launch_process` tiene `shell=True` deshabilitado por seguridad — no expandimos variables de entorno (`%USERPROFILE%`) ni glob. Usa rutas absolutas o relativas literales.
- No espera a que el usuario cierre Explorer — el step se marca como completo apenas el proceso se lanza.

## 🎮 Control que tienes

- Distintos contextos para distintas carpetas: registra varios `configs/<id>.json` o usa overrides por API.
- Programable: ej. abrir la carpeta del proyecto al iniciar sesión.

## 📤 Salidas

Solo registro en SQLite del run con `launch_result.pid` y el comando ejecutado. Sin archivos generados.

## ⚡ Ejecución

Desde el panel: **Ejecutar** → `Alt+0` o click en la card.

CLI:

```bash
flujo run flows/10_explorer_open_path
```
