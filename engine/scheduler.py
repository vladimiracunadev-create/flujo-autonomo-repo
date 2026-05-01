from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from engine.catalog import get_flow_by_folder
from engine.database import (
    acquire_run_lock,
    init_db,
    list_schedules,
    mark_schedule_run,
    release_run_lock,
)
from engine.orchestrator import Orchestrator


class SchedulerService:
    """Bucle simple que dispara flows según schedules en SQLite.

    - Persiste estado en la tabla ``schedules`` (intervalo o cron).
    - Concurrencia: usa ``run_locks`` para evitar lanzar el mismo flow dos
      veces en paralelo aunque haya múltiples instancias del scheduler vivas.
    - Tolerante a fallos: una excepción del orquestador se loggea pero no
      mata el loop.
    """

    def __init__(self, loop_sleep_seconds: float = 2.0) -> None:
        init_db()
        self.loop_sleep_seconds = loop_sleep_seconds
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def start_in_background(self) -> 'SchedulerService':
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return self

    @staticmethod
    def _should_run(schedule: Dict[str, Any]) -> bool:
        if not int(schedule.get('enabled') or 0):
            return False
        next_run_at = schedule.get('next_run_at')
        if not next_run_at:
            return False
        due = datetime.fromisoformat(str(next_run_at).replace('Z', '+00:00'))
        return due <= datetime.now(timezone.utc)

    def _run_job(self, folder: str, interval_seconds: Optional[int], cron_expression: Optional[str]) -> None:
        run_id = datetime.now(timezone.utc).strftime('sched_%Y%m%dT%H%M%S%fZ')
        if not acquire_run_lock(folder, run_id):
            return
        try:
            flow = get_flow_by_folder(folder)
            if not flow:
                return
            try:
                Orchestrator(Path(flow['flow_path'])).run()
            except Exception:
                # No interrumpe el loop. El error queda en la corrida.
                pass
            mark_schedule_run(folder, interval_seconds, cron_expression)
        finally:
            release_run_lock(folder, run_id)

    def run_pending_once(self) -> None:
        for schedule in list_schedules():
            folder = str(schedule['folder'])
            if self._should_run(schedule):
                interval_seconds = schedule.get('interval_seconds')
                cron_expression = schedule.get('cron_expression')
                thread = threading.Thread(
                    target=self._run_job,
                    args=(folder, interval_seconds, cron_expression),
                    daemon=True,
                )
                thread.start()

    def serve_forever(self) -> None:
        while not self._stop.is_set():
            self.run_pending_once()
            time.sleep(self.loop_sleep_seconds)
