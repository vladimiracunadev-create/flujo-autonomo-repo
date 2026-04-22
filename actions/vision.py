from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from plugins.analyzers.base import AnalyzerProtocol
from plugins.analyzers.metadata_image_analyzer import MetadataImageAnalyzer
from plugins.analyzers.mock_image_analyzer import MockImageAnalyzer
from plugins.analyzers.ocr_image_analyzer import OCRImageAnalyzer
from plugins.analyzers.vision_model_analyzer import VisionModelAnalyzer


ANALYZERS: dict[str, AnalyzerProtocol] = {
    'mock': MockImageAnalyzer(),
    'metadata': MetadataImageAnalyzer(),
    'ocr': OCRImageAnalyzer(),
}

VISION_ANALYZER = VisionModelAnalyzer()


def analyze_image(image_path: str, analyzer: str = 'mock') -> Dict[str, Any]:
    target = Path(image_path)
    if not target.exists():
        raise FileNotFoundError(f'Imagen no encontrada: {image_path}')
    analyzer_impl = ANALYZERS.get(analyzer)
    if analyzer_impl is None:
        raise ValueError(f'Analizador desconocido: {analyzer}')
    result = analyzer_impl.analyze(target)
    return {
        'image_path': str(target),
        'analyzer': analyzer,
        **result,
    }


def ocr_image(image_path: str) -> Dict[str, Any]:
    return analyze_image(image_path=image_path, analyzer='ocr')


def find_text_in_image(image_path: str, query: str, case_sensitive: bool = False) -> Dict[str, Any]:
    ocr_result = ocr_image(image_path)
    matches: List[Dict[str, Any]] = []
    query_norm = query if case_sensitive else query.lower()
    for item in ocr_result.get('matches', []):
        text = item.get('text', '')
        probe = text if case_sensitive else text.lower()
        if query_norm in probe:
            matches.append(item)
    return {
        'image_path': image_path,
        'query': query,
        'matched': bool(matches),
        'matches': matches,
        'first_match': matches[0] if matches else None,
        'match_count': len(matches),
        'ocr_text_preview': ocr_result.get('text', '')[:1000],
    }


def select_image(image_path: str) -> Dict[str, Any]:
    target = Path(image_path)
    if not target.exists():
        raise FileNotFoundError(f'Imagen no encontrada: {image_path}')
    return {
        'image_path': str(target),
        'source': 'existing_file',
        'exists': True,
    }


def _normalize_bbox(value: Any) -> Dict[str, Any] | None:
    if not value or not isinstance(value, dict):
        return None
    keys = {'left', 'top', 'width', 'height'}
    if not keys.issubset(set(value.keys())):
        return None
    return {
        'left': int(value.get('left', 0)),
        'top': int(value.get('top', 0)),
        'width': int(value.get('width', 0)),
        'height': int(value.get('height', 0)),
    }


def inspect_screen_target(
    image_path: str,
    mode: str = 'hybrid',
    query_text: str = '',
    vision_provider: str = 'mock',
    vision_model: str | None = None,
    vision_endpoint: str | None = None,
    vision_prompt: str = '',
    vision_api_key: str | None = None,
    vision_api_key_env: str | None = None,
    fallback_bbox: Dict[str, Any] | None = None,
    prefer_source: str = 'ocr',
    timeout_seconds: int = 45,
) -> Dict[str, Any]:
    target = Path(image_path)
    if not target.exists():
        raise FileNotFoundError(f'Imagen no encontrada: {image_path}')

    mode = (mode or 'hybrid').strip().lower()
    prefer_source = (prefer_source or 'ocr').strip().lower()
    diagnostics: List[Dict[str, Any]] = []
    ocr_payload: Dict[str, Any] | None = None
    vision_payload: Dict[str, Any] | None = None
    ocr_target: Dict[str, Any] | None = None
    vision_target: Dict[str, Any] | None = None

    if mode in {'ocr', 'hybrid'}:
        try:
            ocr_payload = ocr_image(str(target))
            matches = ocr_payload.get('matches', [])
            if query_text:
                probe = query_text.lower()
                selected = [item for item in matches if probe in str(item.get('text', '')).lower()]
                if selected:
                    ocr_target = selected[0]
            elif matches:
                ocr_target = matches[0]
        except Exception as exc:  # noqa: BLE001
            diagnostics.append({'source': 'ocr', 'status': 'error', 'message': str(exc)})

    if mode in {'vision', 'hybrid'}:
        try:
            effective_prompt = vision_prompt or (
                f'Localiza en la captura el objetivo visual relacionado con: {query_text!r}. '
                'Responde SOLO JSON con summary, target_found, confidence, target_bbox {left,top,width,height}, visible_text.'
            )
            vision_payload = VISION_ANALYZER.analyze(
                target,
                provider=vision_provider,
                prompt=effective_prompt,
                model=vision_model,
                endpoint=vision_endpoint,
                api_key=vision_api_key,
                api_key_env=vision_api_key_env,
                timeout_seconds=timeout_seconds,
            )
            parsed = vision_payload.get('parsed') or {}
            if parsed.get('target_found'):
                vision_target = _normalize_bbox(parsed.get('target_bbox'))
        except Exception as exc:  # noqa: BLE001
            diagnostics.append({'source': 'vision', 'status': 'error', 'message': str(exc)})

    fallback_normalized = _normalize_bbox(fallback_bbox)
    if not ocr_target and not vision_target and fallback_normalized:
        diagnostics.append({
            'source': 'fallback_bbox',
            'status': 'used',
            'message': 'No hubo detección directa; se usó bounding box configurado.',
        })

    selected_source = None
    selected_bbox = None
    if mode == 'ocr':
        if ocr_target:
            selected_source, selected_bbox = 'ocr', _normalize_bbox(ocr_target)
    elif mode == 'vision':
        if vision_target:
            selected_source, selected_bbox = 'vision', vision_target
    else:
        ordered = [('ocr', _normalize_bbox(ocr_target)), ('vision', vision_target)]
        if prefer_source == 'vision':
            ordered = [('vision', vision_target), ('ocr', _normalize_bbox(ocr_target))]
        for source_name, candidate in ordered:
            if candidate:
                selected_source, selected_bbox = source_name, candidate
                break

    if not selected_bbox and fallback_normalized:
        selected_source, selected_bbox = 'fallback_bbox', fallback_normalized

    target_found = bool(selected_bbox)
    summary_parts = [f'Modo de análisis: {mode}.']
    if target_found:
        summary_parts.append(f'Objetivo detectado vía {selected_source}.')
    else:
        summary_parts.append('No se detectó objetivo clickeable; corresponde recuperación u observación.')
    if diagnostics:
        summary_parts.append(f'Diagnósticos: {len(diagnostics)} evento(s).')

    return {
        'image_path': str(target),
        'mode': mode,
        'query_text': query_text,
        'target_found': target_found,
        'target_bbox': selected_bbox,
        'selected_source': selected_source,
        'decision': 'click' if target_found else 'recover',
        'summary': ' '.join(summary_parts),
        'ocr': ocr_payload,
        'vision': vision_payload,
        'diagnostics': diagnostics,
        'fallback_bbox': fallback_normalized,
    }
