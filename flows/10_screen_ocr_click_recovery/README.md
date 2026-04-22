# 10 Screen OCR Click Recovery

**Familia:** pantalla / escritorio.

Captura pantalla, busca un texto por OCR y hace click en su bounding box. Si no encuentra objetivo o falla OCR, ejecuta una hotkey de recuperación.

## Cuándo Usarlo

- automatizar una acción visual basada en texto;
- probar OCR con coordenadas;
- validar ruta de recuperación.

## Contexto

```json
{
  "query_text": "Guardar",
  "recovery_hotkey": ["esc"]
}
```

## Salida

- captura inicial;
- resultado OCR;
- click o recuperación;
- captura posterior;
- reporte JSON.

## Riesgos

Puede hacer click real. Revisa coordenadas y entorno antes de usarlo sobre aplicaciones importantes.

## Ejecución

```bash
python -m engine.runner run flows/10_screen_ocr_click_recovery
```
