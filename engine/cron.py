"""Cálculo de la siguiente ejecución para una expresión cron de 5 campos.

Soporta:
- ``*`` y números absolutos
- listas: ``1,3,5``
- rangos: ``9-17``
- pasos: ``*/5`` o ``0-30/10``

No soporta nombres simbólicos (``MON``, ``JAN``) ni ``L``/``W``/``#``.
Es deliberadamente pequeño: cubre los casos comunes de "cada N minutos",
"a las HH:MM", "lunes a viernes", sin meter una dependencia externa.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


class CronExpressionError(ValueError):
    pass


@dataclass(frozen=True)
class CronField:
    values: list[int]


_FIELD_RANGES = (
    (0, 59),   # minute
    (0, 23),   # hour
    (1, 31),   # day of month
    (1, 12),   # month
    (0, 6),    # day of week (0=lunes, 6=domingo, estilo ISO)
)


def _parse_field(spec: str, low: int, high: int) -> CronField:
    if spec == '*':
        return CronField(list(range(low, high + 1)))
    values: list[int] = []
    for part in spec.split(','):
        step = 1
        if '/' in part:
            base, step_str = part.split('/', 1)
            step = int(step_str)
            if step <= 0:
                raise CronExpressionError(f'Paso inválido en {part!r}')
            part = base
        if part == '*':
            start, end = low, high
        elif '-' in part:
            start_s, end_s = part.split('-', 1)
            start, end = int(start_s), int(end_s)
        else:
            start = end = int(part)
        if start < low or end > high or start > end:
            raise CronExpressionError(f'Rango fuera de límites en {part!r} ({low}-{high})')
        values.extend(range(start, end + 1, step))
    return CronField(sorted(set(values)))


def parse_cron(expression: str) -> list[CronField]:
    parts = expression.strip().split()
    if len(parts) != 5:
        raise CronExpressionError(
            f"Se esperaban 5 campos cron (min hour dom month dow), se recibieron {len(parts)}: {expression!r}"
        )
    return [_parse_field(part, low, high) for part, (low, high) in zip(parts, _FIELD_RANGES, strict=False)]


def _iso_weekday(dt: datetime) -> int:
    """Lunes=0 ... Domingo=6 (consistente con isoweekday-1)."""
    return dt.weekday()


def next_after(expression: str, after: datetime) -> datetime:
    """Devuelve la próxima fecha en UTC que matchea ``expression``, estrictamente posterior a ``after``."""
    fields = parse_cron(expression)
    minutes, hours, days, months, dows = fields

    candidate = (after + timedelta(minutes=1)).replace(second=0, microsecond=0)
    if candidate.tzinfo is None:
        candidate = candidate.replace(tzinfo=timezone.utc)

    # límite generoso para evitar bucles patológicos (≈ 4 años)
    for _ in range(60 * 24 * 366 * 4):
        if candidate.month not in months.values:
            # saltar al primer minuto del mes siguiente
            year = candidate.year + (1 if candidate.month == 12 else 0)
            month = 1 if candidate.month == 12 else candidate.month + 1
            candidate = datetime(year, month, 1, 0, 0, tzinfo=timezone.utc)
            continue
        if candidate.day not in days.values:
            candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0)
            continue
        if _iso_weekday(candidate) not in dows.values:
            candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0)
            continue
        if candidate.hour not in hours.values:
            candidate = (candidate + timedelta(hours=1)).replace(minute=0)
            continue
        if candidate.minute not in minutes.values:
            candidate = candidate + timedelta(minutes=1)
            continue
        return candidate
    raise CronExpressionError(f'No se encontró próxima ejecución dentro de un horizonte razonable: {expression}')


def validate(expression: str) -> str | None:
    try:
        parse_cron(expression)
        return None
    except CronExpressionError as exc:
        return str(exc)
