from __future__ import annotations

from typing import Dict, List


def prioritize_steps(step_ids: List[str], context: Dict[str, object]) -> List[str]:
    """Punto simple para decidir orden sin romper el motor.

    Hoy devuelve el mismo orden. Aquí puedes introducir reglas duras o IA opcional.
    """
    return step_ids
