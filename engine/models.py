from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TransitionDefinition:
    on: str = "success"
    next_step: Optional[str] = None
    end: bool = False
    when: Optional[Dict[str, Any]] = None


@dataclass
class StepDefinition:
    id: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    save_as: Optional[str] = None
    retries: int = 0
    when: Optional[Dict[str, Any]] = None
    transitions: List[TransitionDefinition] = field(default_factory=list)


@dataclass
class FlowDefinition:
    id: str
    name: str
    steps: List[StepDefinition]
    description: str = ""
    family: str = "general"
    start_step: Optional[str] = None
    max_steps_per_run: int = 200
