from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from engine.database import insert_event


class JsonlLogger:
    def __init__(self, log_path: Path, run_id: str) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id

    def write(self, event_type: str, payload: Dict[str, Any]) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            'timestamp': timestamp,
            'event': event_type,
            **payload,
        }
        with self.log_path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')
        insert_event(self.run_id, event_type, payload, event_time=timestamp)
