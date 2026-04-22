from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from engine.catalog import get_flow_by_folder
from engine.database import get_schedule, init_db, list_schedules, mark_schedule_run
from engine.orchestrator import Orchestrator


class SchedulerService:
    def __init__(self, loop_sleep_seconds: float = 2.0) -> None:
        init_db()
        self.loop_sleep_seconds = loop_sleep_seconds
        self._stop = threading.Event()
        self._running: Dict[str, bool] = {}

    def stop(self) -> None:
        self._stop.set()

    def start_in_background(self) -> 'SchedulerService':
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return self

    def _should_run(self, schedule: Dict[str, object]) -> bool:
        if not int(schedule.get('enabled') or 0):
            return False
        next_run_at = schedule.get('next_run_at')
        if not next_run_at:
            return False
        due = datetime.fromisoformat(str(next_run_at).replace('Z', '+00:00'))
        return due <= datetime.now(timezone.utc)

    def _run_job(self, folder: str, interval_seconds: Optional[int]) -> None:
        self._running[folder] = True
        try:
            flow = get_flow_by_folder(folder)
            if not flow:
                return
            orchestrator = Orchestrator(Path(flow['flow_path']))
            orchestrator.run()
            mark_schedule_run(folder, interval_seconds)
        except Exception:
            mark_schedule_run(folder, interval_seconds)
        finally:
            self._running[folder] = False

    def run_pending_once(self) -> None:
        for schedule in list_schedules():
            folder = str(schedule['folder'])
            if self._running.get(folder):
                continue
            if self._should_run(schedule):
                interval_seconds = schedule.get('interval_seconds')
                thread = threading.Thread(target=self._run_job, args=(folder, interval_seconds), daemon=True)
                thread.start()

    def serve_forever(self) -> None:
        while not self._stop.is_set():
            self.run_pending_once()
            time.sleep(self.loop_sleep_seconds)
