"""Agregaciones simples sobre la tabla ``runs`` y ``steps`` para el panel."""
from __future__ import annotations

from typing import Any, Dict, List

from engine.database import connect


def overview(window_runs: int = 200) -> Dict[str, Any]:
    """Resumen global: totales por estado, duración promedio y top fallos."""
    with connect() as conn:
        totals = {row['status']: row['c'] for row in conn.execute(
            'SELECT status, COUNT(*) AS c FROM runs GROUP BY status'
        ).fetchall()}
        avg_duration = conn.execute(
            'SELECT AVG(duration_seconds) AS avg_d FROM runs WHERE duration_seconds IS NOT NULL'
        ).fetchone()['avg_d']
        recent = conn.execute(
            'SELECT status, duration_seconds FROM runs ORDER BY created_at DESC LIMIT ?',
            (window_runs,),
        ).fetchall()
        recent_ok = sum(1 for r in recent if r['status'] == 'completed')
        recent_failed = sum(1 for r in recent if r['status'] == 'failed')
        recent_duration = [r['duration_seconds'] for r in recent if r['duration_seconds'] is not None]
        slowest_steps = [dict(row) for row in conn.execute(
            '''
            SELECT action, AVG(duration_seconds) AS avg_d, COUNT(*) AS c
            FROM steps
            WHERE duration_seconds IS NOT NULL
            GROUP BY action
            ORDER BY avg_d DESC
            LIMIT 10
            '''
        ).fetchall()]
        retries_by_action = [dict(row) for row in conn.execute(
            '''
            SELECT action, SUM(attempt - 1) AS retry_count
            FROM steps
            WHERE attempt > 1
            GROUP BY action
            ORDER BY retry_count DESC
            LIMIT 10
            '''
        ).fetchall()]
        failed_actions = [dict(row) for row in conn.execute(
            '''
            SELECT action, COUNT(*) AS c
            FROM steps
            WHERE status = 'failed'
            GROUP BY action
            ORDER BY c DESC
            LIMIT 10
            '''
        ).fetchall()]
    return {
        'totals_by_status': totals,
        'average_duration_seconds': avg_duration,
        'window': {
            'size': window_runs,
            'completed': recent_ok,
            'failed': recent_failed,
            'avg_duration_seconds': sum(recent_duration) / len(recent_duration) if recent_duration else None,
        },
        'slowest_actions': slowest_steps,
        'retries_top_actions': retries_by_action,
        'failed_top_actions': failed_actions,
    }


def by_flow(limit: int = 50) -> List[Dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            '''
            SELECT flow_id,
                   COUNT(*) AS runs_total,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS runs_completed,
                   SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS runs_failed,
                   AVG(duration_seconds) AS avg_duration_seconds,
                   MAX(created_at) AS last_run_at
            FROM runs
            GROUP BY flow_id
            ORDER BY runs_total DESC
            LIMIT ?
            ''',
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def prometheus_text() -> str:
    """Exposición Prometheus-text con un puñado de métricas útiles."""
    o = overview()
    lines: List[str] = []
    lines.append('# HELP flujo_runs_total Total de corridas por estado.')
    lines.append('# TYPE flujo_runs_total counter')
    for status, count in (o['totals_by_status'] or {}).items():
        lines.append(f'flujo_runs_total{{status="{status}"}} {count}')
    avg = o.get('average_duration_seconds')
    if avg is not None:
        lines.append('# HELP flujo_run_duration_seconds_avg Duración promedio histórica.')
        lines.append('# TYPE flujo_run_duration_seconds_avg gauge')
        lines.append(f'flujo_run_duration_seconds_avg {avg}')
    window = o.get('window') or {}
    if window:
        lines.append(f'flujo_runs_window_completed {window.get("completed", 0)}')
        lines.append(f'flujo_runs_window_failed {window.get("failed", 0)}')
    return '\n'.join(lines) + '\n'
