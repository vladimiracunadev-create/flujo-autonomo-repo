# ⚙️ Abrir Configuración de Windows en sección

## 🎯 Para qué sirve

Abrir la app **Configuración** (Settings) de Windows directamente en una pestaña específica. Aprovecha el esquema URI `ms-settings:` que Windows expone para deep-linkear cualquier sección sin navegación manual.

Casos de uso:

- Diagnóstico de red: 1 clic → `ms-settings:network` directo a Estado de la red.
- Auditoría visual: capturar la sección "Privacidad → Cámara" antes y después de instalar un driver.
- Soporte remoto: "ejecuta este flow" en vez de dictar la ruta menú por menú.

## 🧭 Flujo paso a paso

1. **open_settings_section** → `webbrowser.open("ms-settings:<section>")`. Windows asocia este esquema con la app Settings y abre la pestaña pedida.

## ⚙️ Configuración

| Campo | Tipo | Por defecto | Significado |
| --- | --- | --- | --- |
| `section` | string | `network` | Identificador de la sección de Settings (sin el prefijo `ms-settings:`). |

### Secciones útiles (`section`)

| Valor | Abre en |
| --- | --- |
| `network` | Estado de la red |
| `network-wifi` | Wi-Fi |
| `display` | Pantalla |
| `sound` | Sonido |
| `bluetooth` | Bluetooth y otros dispositivos |
| `printers` | Impresoras y escáneres |
| `appsfeatures` | Aplicaciones instaladas |
| `defaultapps` | Aplicaciones predeterminadas |
| `privacy-camera` | Privacidad → Cámara |
| `privacy-microphone` | Privacidad → Micrófono |
| `windowsupdate` | Windows Update |
| `storagesense` | Almacenamiento |
| `keyboard` | Teclado |
| `mouse` | Mouse |

Lista completa: <https://learn.microsoft.com/windows/uwp/launch-resume/launch-settings-app>.

## 📋 Requisitos

- Windows 10 / 11 con la app Configuración disponible (lo está por defecto).
- No requiere `pyautogui` ni captura.

## 🛡️ Sandbox sugerido

```json
"allowed_actions": ["ui.open_url"],
"max_runtime_seconds": 5
```

Aplicado. No toca filesystem, no usa internet (a pesar de que `ui.open_url` también sirve para http/https — aquí se restringe al uso `ms-settings:`).

## ⚠️ Limitaciones honestas

- No funciona en Windows Server con la app Settings deshabilitada por política de grupo.
- No funciona en Linux/macOS (el esquema `ms-settings:` es propio de Windows).
- No interactúa con la sección abierta — solo la lleva al frente. Si quieres hacer clic en algún toggle, hay que sumar pasos con `ui.click_bbox` u `ocr_image` después.
- La sección abre **en la pantalla principal** y puede no quedar enfocada si otra app reclama foco al mismo tiempo.

## 🎮 Control que tienes

- Crea distintos `configs/<id>_<section>.json` para tener varios atajos predefinidos a distintas secciones.
- Encadenable con `12_desktop_ocr_inventory` para auditoría: abre Settings → captura → OCR del contenido visible.

## 📤 Salidas

Solo registro en SQLite con el URI ejecutado. Sin archivos generados.

## ⚡ Ejecución

Desde el panel: **Ejecutar** → `Alt+-` o click en la card.

CLI:

```bash
flujo run flows/11_settings_open_section
```
