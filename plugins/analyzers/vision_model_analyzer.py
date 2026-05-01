from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageStat


def _image_to_data_url(image_path: Path) -> str:
    mime = 'image/png'
    suffix = image_path.suffix.lower()
    if suffix in {'.jpg', '.jpeg'}:
        mime = 'image/jpeg'
    elif suffix == '.webp':
        mime = 'image/webp'
    encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
    return f'data:{mime};base64,{encoded}'


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r'\{.*\}', text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


class VisionModelAnalyzer:
    """Analizador de visión multimodal desacoplado.

    Soporta tres proveedores:
    - mock: no usa IA externa; genera una lectura heurística de la imagen.
    - openai_compatible: endpoint estilo /chat/completions.
    - ollama: endpoint local tipo Ollama con soporte de imágenes.
    """

    def analyze(
        self,
        image_path: Path,
        *,
        provider: str = 'mock',
        prompt: str = '',
        model: str | None = None,
        endpoint: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout_seconds: int = 45,
    ) -> dict[str, Any]:
        provider = (provider or 'mock').strip().lower()
        if provider == 'mock':
            return self._analyze_mock(image_path=image_path, prompt=prompt)
        if provider == 'openai_compatible':
            return self._analyze_openai_compatible(
                image_path=image_path,
                prompt=prompt,
                model=model,
                endpoint=endpoint,
                api_key=api_key,
                api_key_env=api_key_env,
                timeout_seconds=timeout_seconds,
            )
        if provider == 'ollama':
            return self._analyze_ollama(
                image_path=image_path,
                prompt=prompt,
                model=model,
                endpoint=endpoint,
                timeout_seconds=timeout_seconds,
            )
        raise ValueError(f'Proveedor de visión no soportado: {provider}')

    def _analyze_mock(self, image_path: Path, prompt: str = '') -> dict[str, Any]:
        with Image.open(image_path) as img:
            rgb = img.convert('RGB')
            stat = ImageStat.Stat(rgb)
            mean_rgb = [round(value, 2) for value in stat.mean]
            avg_brightness = round(sum(mean_rgb) / 3, 2)
            width, height = rgb.width, rgb.height

        if avg_brightness < 60:
            visual_state = 'oscuro'
        elif avg_brightness < 180:
            visual_state = 'medio'
        else:
            visual_state = 'claro'

        summary = (
            'Visión mock completada sin OCR ni proveedor externo. '
            'Sirve para probar el flujo y dejar trazabilidad, pero no identifica texto real.'
        )
        if prompt:
            summary += ' Prompt recibido para auditoría.'

        return {
            'provider': 'mock',
            'summary': summary,
            'prompt': prompt,
            'raw_response': None,
            'parsed': {
                'summary': summary,
                'visible_state': visual_state,
                'target_found': False,
                'target_bbox': None,
                'confidence': 0.0,
            },
            'image_metadata': {
                'width': width,
                'height': height,
                'mean_rgb': mean_rgb,
                'avg_brightness': avg_brightness,
            },
        }

    def _analyze_openai_compatible(
        self,
        *,
        image_path: Path,
        prompt: str,
        model: str | None,
        endpoint: str | None,
        api_key: str | None,
        api_key_env: str | None,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        if not endpoint:
            raise RuntimeError('Debes indicar vision_endpoint para usar openai_compatible.')
        if not model:
            raise RuntimeError('Debes indicar vision_model para usar openai_compatible.')
        token = api_key or (os.getenv(api_key_env) if api_key_env else None) or os.getenv('OPENAI_API_KEY')
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        data_url = _image_to_data_url(image_path)
        instruction = prompt or (
            'Analiza la captura y responde SOLO JSON con: '
            'summary, target_found, confidence, target_bbox {left,top,width,height}, visible_text.'
        )
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': instruction},
                        {'type': 'image_url', 'image_url': {'url': data_url}},
                    ],
                }
            ],
            'temperature': 0,
        }
        url = endpoint.rstrip('/') + '/chat/completions'
        response = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
        raw_text = body['choices'][0]['message']['content']
        parsed = _extract_json_object(raw_text) or {'summary': raw_text, 'target_found': False, 'target_bbox': None}
        return {
            'provider': 'openai_compatible',
            'endpoint': url,
            'model': model,
            'prompt': instruction,
            'raw_response': raw_text,
            'parsed': parsed,
        }

    def _analyze_ollama(
        self,
        *,
        image_path: Path,
        prompt: str,
        model: str | None,
        endpoint: str | None,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        if not model:
            raise RuntimeError('Debes indicar vision_model para usar Ollama.')
        base_url = (endpoint or 'http://127.0.0.1:11434').rstrip('/')
        image_b64 = base64.b64encode(image_path.read_bytes()).decode('ascii')
        instruction = prompt or (
            'Analiza la captura y responde SOLO JSON con: '
            'summary, target_found, confidence, target_bbox {left,top,width,height}, visible_text.'
        )
        payload = {
            'model': model,
            'stream': False,
            'messages': [
                {
                    'role': 'user',
                    'content': instruction,
                    'images': [image_b64],
                }
            ],
        }
        url = base_url + '/api/chat'
        response = requests.post(url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
        raw_text = body.get('message', {}).get('content', '')
        parsed = _extract_json_object(raw_text) or {'summary': raw_text, 'target_found': False, 'target_bbox': None}
        return {
            'provider': 'ollama',
            'endpoint': url,
            'model': model,
            'prompt': instruction,
            'raw_response': raw_text,
            'parsed': parsed,
        }
