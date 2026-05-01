"""Política de seguridad por flow.

Cada manifest puede declarar restricciones que el orquestador hace cumplir
antes y durante la ejecución:

- ``allowed_actions``: lista blanca de nombres de acción.
- ``required_secrets``: variables de entorno que deben existir antes de correr.
- ``allowed_paths``: prefijos de ruta donde el flow puede leer/escribir.
- ``max_runtime_seconds``: corta el flow si la corrida supera este tiempo.

El módulo expone una clase ``SandboxPolicy`` que se aplica desde el orquestador.
La política nunca es opcional para el motor: si no hay restricciones, se usa
una política permisiva por defecto que sólo registra los hechos.
"""
from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SandboxViolation(Exception):
    """Se eleva cuando un flow intenta salir de su política."""


@dataclass
class SandboxPolicy:
    allowed_actions: list[str] | None = None
    required_secrets: list[str] = field(default_factory=list)
    allowed_paths: list[str] | None = None
    max_runtime_seconds: float | None = None

    @classmethod
    def from_manifest(cls, manifest: dict[str, Any]) -> SandboxPolicy:
        return cls(
            allowed_actions=list(manifest['allowed_actions']) if manifest.get('allowed_actions') else None,
            required_secrets=list(manifest.get('required_secrets') or []),
            allowed_paths=list(manifest['allowed_paths']) if manifest.get('allowed_paths') else None,
            max_runtime_seconds=(
                float(manifest['max_runtime_seconds'])
                if manifest.get('max_runtime_seconds') is not None
                else None
            ),
        )

    def check_required_secrets(self) -> list[str]:
        missing = [name for name in self.required_secrets if not os.environ.get(name)]
        return missing

    def assert_secrets_present(self) -> None:
        missing = self.check_required_secrets()
        if missing:
            raise SandboxViolation(
                f"Faltan variables de entorno requeridas por el flow: {', '.join(missing)}"
            )

    def assert_action_allowed(self, action_name: str) -> None:
        if self.allowed_actions is not None and action_name not in self.allowed_actions:
            raise SandboxViolation(
                f"Acción '{action_name}' bloqueada por allowed_actions del manifest"
            )

    def _path_strings(self, params: Any) -> Iterable[str]:
        if isinstance(params, dict):
            for key, value in params.items():
                if any(token in key.lower() for token in ('path', 'destination', 'source', 'output', 'file')):
                    if isinstance(value, str):
                        yield value
                yield from self._path_strings(value)
        elif isinstance(params, list):
            for item in params:
                yield from self._path_strings(item)

    def assert_paths_allowed(self, params: Any) -> None:
        if not self.allowed_paths:
            return
        allowed_resolved = [Path(p).resolve() for p in self.allowed_paths]
        for raw in self._path_strings(params):
            if not raw or '{' in raw:  # placeholders sin resolver: el motor los resuelve antes
                continue
            target = Path(raw).resolve()
            if not any(self._is_under(target, base) for base in allowed_resolved):
                raise SandboxViolation(
                    f"Ruta fuera de allowed_paths: {raw} (bases: {self.allowed_paths})"
                )

    @staticmethod
    def _is_under(target: Path, base: Path) -> bool:
        try:
            target.relative_to(base)
            return True
        except ValueError:
            return False

    def is_permissive(self) -> bool:
        return (
            self.allowed_actions is None
            and not self.required_secrets
            and self.allowed_paths is None
            and self.max_runtime_seconds is None
        )

    def summary(self) -> dict[str, Any]:
        return {
            'allowed_actions': self.allowed_actions,
            'required_secrets': self.required_secrets,
            'allowed_paths': self.allowed_paths,
            'max_runtime_seconds': self.max_runtime_seconds,
            'permissive': self.is_permissive(),
        }
