from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image


class OCRImageAnalyzer:
    def analyze(self, image_path: Path) -> dict[str, Any]:
        try:
            import pytesseract
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                'pytesseract no está instalado. Agrega la dependencia y asegúrate de tener Tesseract OCR en el equipo.'
            ) from exc

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
        }
