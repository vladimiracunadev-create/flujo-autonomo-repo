# 📋 07 · Llenado y validación de formulario web

> Lanza Chromium visible, navega al formulario `data/web/form_demo.html`, genera 10 datos random, los llena uno por uno con efecto observable, dispara submit, espera validación JS y devuelve los datos.

| | |
| --- | --- |
| **Familia** | navegador |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS |
| **Internet** | ❌ no requerido (página local) |
| **Modifica el sistema** | ⚠️ abre ventana de Chromium visible |
| **Salida** | 📊 JSON (sin PNG) |

---

## 🎯 Para qué sirve

- 🤖 Demostrar **automatización web real**: apertura, llenado, validación, guardado.
- 📋 Plantilla para flujos E2E sobre formularios internos: completar registros, dar de alta usuarios, enviar reportes.
- 🧪 Generar datos sintéticos y validarlos contra reglas del DOM.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `fill_and_submit_form` | `browser.fill_form` | Lanza Chromium con `slow_mo`, navega a `target_url`, rellena los 10 campos del formulario uno por uno (observable), submit, espera `#validation-result.show`, lee `validation_text` y `submitted_payload`, guarda JSON. |

### Los 10 campos del formulario

```
nombre · apellido · email · telefono · direccion ·
ciudad · pais (select) · fecha_nacimiento · profesion · comentario (textarea)
```

## ⚙️ Configuración

```json
{
  "target_url": "data/web/form_demo.html",
  "headless": false,
  "slow_mo_ms": 250,
  "viewport_width": 1280,
  "viewport_height": 900
}
```

| Clave | Tipo | Efecto |
| --- | --- | --- |
| `target_url` | string | URL `http://`/`https://` o ruta local. Por defecto el HTML de demo del repo. |
| `headless` | bool | `false` (default) abre ventana **visible** de Chromium. `true` corre invisible para CI. |
| `slow_mo_ms` | int | Milisegundos entre cada acción de Playwright. Subirlo para ver mejor el llenado. |
| `viewport_width/height` | int | Dimensiones de la ventana del browser. |

## 📋 Requisitos

- ✅ `playwright` Python: `pip install playwright`
- ✅ Chromium descargado: `python -m playwright install chromium`
- ⚠️ Si `headless=false`, requiere sesión gráfica para mostrar la ventana.

## 📤 Salida (solo datos)

`output/reports/form_submission_<ts>.json` ejemplo:

```json
{
  "url": "file:///.../data/web/form_demo.html",
  "data_sent": {
    "nombre": "Juan", "apellido": "Pérez",
    "email": "juan.perez42@mail.com", "telefono": "+56 9 12345678",
    "direccion": "Av. Libertad 1234", "ciudad": "Santiago", "pais": "CL",
    "fecha_nacimiento": "1990-04-15", "profesion": "Ingeniero",
    "comentario": "Este registro fue generado automáticamente..."
  },
  "validation_text": "✅ Formulario válido y guardado · 10 campos validados",
  "is_success": true,
  "submitted_visible": true,
  "submitted_payload": "{...}"
}
```

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["browser.fill_form"],
  "allowed_paths": ["data/web", "output/reports"],
  "max_runtime_seconds": 60
}
```

## ⚠️ Limitaciones honestas

- ⚠️ Con `headless=false` la ventana se abre y cierra en pantalla. Si estás trabajando, te roba el foco un instante.
- ❌ No persiste en una DB externa, solo escribe el JSON en disco.
- ❌ La página HTML está hardcodeada con esos 10 campos. Para otro form, hay que adaptar el código.

## ⚡ Ejecución

```bash
flujo run flows/07_browser_form_filler

# Headless (sin ventana visible) — útil para CI o servidor
# Editar configs/07_browser_form_filler.json y poner "headless": true
```
