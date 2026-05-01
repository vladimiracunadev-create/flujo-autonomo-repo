# 📁 03 · Inventario de carpeta

> Lista una carpeta configurable y genera estadísticas por extensión.

| | |
| --- | --- |
| **Familia** | filesystem |
| **Plataforma** | 🟢 Windows · 🟢 Linux · 🟢 macOS · 🟢 headless |
| **Internet** | ❌ no requerido |
| **Modifica el sistema** | ❌ solo lee y escribe en `output/` |

---

## 🎯 Para qué sirve

- 🗃️ Auditar contenido de carpeta con conteo, tamaño y archivo más grande.
- 📊 Generar evidencia de archivos para reportes operativos.
- 🧪 Probar el motor sin tocar UI ni red. **El flow más seguro y simple del repo**.

## 🧭 Flujo paso a paso

| # | Paso | Acción | Qué hace |
| --- | --- | --- | --- |
| 1 | `scan_folder` | `filesystem.list_directory` | Lista archivos en `path_override`, no recursivo. |
| 2 | `classify_inventory` | `filesystem.classify_file_inventory` | Agrega: total, suma bytes, distribución por ext, archivo mayor. |
| 3 | `write_inventory` | `filesystem.write_json` | Reporte JSON con `inventory` + `stats`. |

## ⚙️ Configuración

`context.example.json`:

```json
{ "path_override": "data/inbox" }
```

| Clave | Tipo | Efecto |
| --- | --- | --- |
| `path_override` | string | Carpeta a inventariar (relativa al workspace o absoluta). |

## 📋 Requisitos

- ✅ Solo Python 3.10+ y stdlib. **NO requiere ninguna lib externa**.

## 🛡️ Sandbox sugerido

```json
{
  "allowed_actions": ["filesystem.list_directory", "filesystem.classify_file_inventory", "filesystem.write_json"],
  "allowed_paths": ["data/", "output/reports"]
}
```

## ⚠️ Limitaciones

- ❌ No es recursivo. Para subcarpetas, copia el manifest y cambia `recursive: true`.
- ❌ Solo cuenta archivos, no directorios.

## 🎮 Control que tienes

| Aspecto | Cómo se cambia |
| --- | --- |
| Carpeta a inventariar | `path_override` en config |
| Recursividad | `recursive: true` en manifest |
| Frecuencia | Scheduler cron (ej: `0 9 * * *`) |

## 📤 Salidas

- 📊 `output/reports/folder_inventory_<ts>.json`:

```json
{
  "inventory": {"path": "data/inbox", "files": [...], "total_files": 12},
  "stats": {
    "total_files": 12, "total_size_bytes": 8421044,
    "by_extension": {".pdf": 3, ".txt": 9},
    "largest_file": {...}
  }
}
```

## ⚡ Ejecución

```bash
flujo run flows/03_folder_inventory
flujo run flows/03_folder_inventory --context configs/03_folder_inventory.json
```
