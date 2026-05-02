from __future__ import annotations

from pathlib import Path
from typing import Any


def _output_root() -> Path:
    """Carpeta donde el motor considera "outputs" reales del flow."""
    return Path('output').resolve()


def extract_existing_paths(data: Any) -> list[dict[str, Any]]:
    """Recorre el state buscando paths que apunten a archivos en ``output/``.

    Antes consideraba cualquier path existente como output; eso contaminaba
    la lista con archivos que el flow solo había leído (p.ej. el dropbox
    de entrada). Ahora limita la detección a archivos bajo ``output/`` que
    es donde los flows del repo escriben sus reportes y capturas.
    """
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    output_root = _output_root()

    def walk(value: Any, trail: str = "root") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{trail}.{key}")
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{trail}[{index}]")
            return
        if not isinstance(value, str):
            return
        # Heurística rápida: paths reales rara vez pasan de ~260 chars en
        # Windows o ~4096 en Linux. Strings largos (descripciones, JSON
        # serializados) NO son paths — saltamos para evitar OSError
        # ENAMETOOLONG al llamar Path.exists() en Linux.
        if len(value) > 260 or '\n' in value:
            return
        try:
            candidate = Path(value)
            if not candidate.exists() or not candidate.is_file():
                return
            resolved = candidate.resolve()
            resolved.relative_to(output_root)
        except (ValueError, OSError):
            # ValueError: no está bajo output_root
            # OSError: nombre muy largo, ruta inválida, permisos, etc.
            return
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        try:
            size = candidate.stat().st_size
        except OSError:
            return
        found.append(
            {
                'path': str(candidate),
                'name': candidate.name,
                'size_bytes': size,
                'source': trail,
            }
        )

    walk(data)
    return sorted(found, key=lambda item: item['path'])
