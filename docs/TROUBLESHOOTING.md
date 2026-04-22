# Troubleshooting

Guía rápida para diagnosticar fallas comunes.

## `ModuleNotFoundError`

Síntoma:

```text
ModuleNotFoundError: No module named 'requests'
```

Solución:

```bash
pip install -r requirements.txt
```

Nota: `python -m engine.runner list` no debería requerir dependencias opcionales.

## SQLite No Puede Abrir La Base

Síntoma:

```text
sqlite3.OperationalError: unable to open database file
```

Revisa:

- que exista `db/`;
- que el usuario tenga permiso de escritura;
- que ningún proceso bloquee `db/runs.db`;
- que el workspace no esté montado como solo lectura.

Prueba:

```bash
python -c "import sqlite3; sqlite3.connect('db/manual_probe.db').close(); print('ok')"
```

## Captura De Pantalla Falla

Síntoma:

```text
No fue posible capturar la pantalla
```

Revisa:

- entorno con escritorio gráfico real;
- permisos de captura;
- sesión remota/headless;
- disponibilidad de `mss` o `Pillow`.

Alternativa para pruebas:

- usa `image_override`;
- activa `skip_after_capture`;
- usa `ui_dry_run`.

## OCR No Encuentra Texto

Revisa:

- Tesseract instalado en el sistema;
- calidad y contraste de la imagen;
- idioma/configuración de OCR;
- que `query_text` coincida parcialmente con el texto visible.

## Click Visual Incorrecto

Antes de usar clicks reales:

1. ejecuta con `ui_dry_run = true`;
2. revisa `analysis.target_bbox`;
3. verifica que `left`, `top`, `width`, `height` correspondan a la pantalla real;
4. solo entonces cambia a `ui_dry_run = false`.

## Scheduler No Ejecuta

Revisa:

- que el scheduler esté activo para el flow;
- que `interval_seconds` sea mayor que cero;
- que `next_run_at` esté vencido;
- que no haya una corrida del mismo flow marcada como en ejecución;
- que el proceso `python -m app.server` o `python -m engine.runner scheduler` siga vivo.

## Panel No Abre

Revisa:

- puerto `8787` disponible;
- firewall local;
- que el comando haya impreso `Panel disponible en http://127.0.0.1:8787`;
- que estés abriendo `127.0.0.1`, no una IP pública.

## Mojibake En Consola

Si ves texto mal acentuado en PowerShell, puede ser un problema de codepage de consola. Los archivos están en UTF-8.

Prueba:

```powershell
chcp 65001
python -c "from pathlib import Path; print(Path('README.md').read_text(encoding='utf-8').splitlines()[0])"
```

## GitHub CLI

Si `gh` no puede operar por permisos de configuración:

```bash
gh auth status
```

Si Git rechaza el repo por ownership distinto:

```bash
git config --global --add safe.directory C:/dev/flujo-autonomo-repo
```
