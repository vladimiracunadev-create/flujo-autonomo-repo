from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from PIL import Image


class OCRImageAnalyzer:
    """Analizador OCR con degradación elegante.

    Si la dependencia Python ``pytesseract`` o el binario externo ``tesseract``
    no están instalados, en lugar de hacer crash devuelve un payload vacío
    con ``status: "unavailable"`` y un mensaje útil. Esto permite que flows
    como ``10_screen_ocr_click_recovery`` no caigan al primer paso y puedan
    seguir su rama de fallback.
    """

    @staticmethod
    def _tesseract_binary_available() -> bool:
        if shutil.which('tesseract'):
            return True
        # Rutas típicas en Windows si no está en PATH
        for candidate in (
            'C:/Program Files/Tesseract-OCR/tesseract.exe',
            'C:/Program Files (x86)/Tesseract-OCR/tesseract.exe',
        ):
            if Path(candidate).exists():
                return True
        return False

    def analyze(self, image_path: Path) -> dict[str, Any]:
        try:
            import pytesseract
        except ImportError:
            return {
                'text': '',
                'matches': [],
                'match_count': 0,
                'summary': 'OCR no disponible: pytesseract no instalado. Instálalo con `pip install pytesseract`.',
                'status': 'unavailable',
                'reason': 'pytesseract_missing',
            }

        if not self._tesseract_binary_available():
            return {
                'text': '',
                'matches': [],
                'match_count': 0,
                'summary': (
                    'OCR no disponible: el binario tesseract no está instalado en el sistema. '
                    'Windows: `choco install tesseract` o descargar de UB Mannheim. '
                    'Linux: `apt-get install tesseract-ocr`. macOS: `brew install tesseract`.'
                ),
                'status': 'unavailable',
                'reason': 'tesseract_binary_missing',
            }

        with Image.open(image_path) as img:
            rgb = img.convert('RGB')
            raw_text = pytesseract.image_to_string(rgb)
            data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)

        matches: list[dict[str, Any]] = []
        for index, text in enumerate(data.get('text', [])):
            clean = (text or '').strip()
            if not clean:
                continue
            matches.append(
                {
                    'text': clean,
                    'conf': data.get('conf', [None])[index],
                    'left': int(data['left'][index]),
                    'top': int(data['top'][index]),
                    'width': int(data['width'][index]),
                    'height': int(data['height'][index]),
                }
            )

        return {
            'text': raw_text.strip(),
            'matches': matches,
            'match_count': len(matches),
            'summary': 'OCR local completado con pytesseract.',
            'status': 'ok',
        }
