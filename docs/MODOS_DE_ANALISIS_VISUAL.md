# Modos de análisis visual

Este repositorio ya no deja el caso de pantalla amarrado solo a OCR. Desde v5 el análisis visual se puede ejecutar en tres modos:

## 1. OCR

Usa `pytesseract` y genera texto estructurado + bounding boxes. Es el modo más útil para:

- botones o labels con texto estable
- auditoría exacta
- histórico consultable
- operación local sin depender de un proveedor externo

## 2. Visión

Usa un modelo multimodal o un proveedor local/remoto para interpretar la pantalla como imagen completa.

Sirve más cuando importa:

- layout de la UI
- íconos
- contexto visual
- pantallas donde el texto no basta

## 3. Híbrido

Combina OCR + visión y decide con prioridad configurable.

Es el modo más sólido para automatización operativa cuando:

- a veces hay texto y a veces no
- el OCR es suficiente en algunas pantallas, pero no en otras
- se quiere trazabilidad y también comprensión visual más rica

## Regla práctica

- **texto claro y repetible** → OCR
- **interfaz visual compleja** → visión
- **proceso robusto para producción** → híbrido
