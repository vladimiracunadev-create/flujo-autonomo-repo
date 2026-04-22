from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def _capture_with_mss(output_path: Path) -> Dict[str, Any]:
    import mss
    import mss.tools

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
        return {
            "image_path": str(output_path),
            "width": sct_img.width,
            "height": sct_img.height,
            "method": "mss",
        }


def _capture_with_pillow(output_path: Path) -> Dict[str, Any]:
    from PIL import ImageGrab

    img = ImageGrab.grab()
    img.save(output_path)
    return {
        "image_path": str(output_path),
        "width": img.width,
        "height": img.height,
        "method": "pillow",
    }


def capture_screenshot(output_path: str) -> Dict[str, Any]:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        return _capture_with_mss(target)
    except Exception:
        try:
            return _capture_with_pillow(target)
        except Exception as exc:
            raise RuntimeError(
                "No fue posible capturar la pantalla. Revisa si el entorno tiene escritorio gráfico disponible."
            ) from exc
