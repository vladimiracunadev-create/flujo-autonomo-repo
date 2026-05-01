from __future__ import annotations


def prioritize_steps(step_ids: list[str], context: dict[str, object]) -> list[str]:
    """Punto simple para decidir orden sin romper el motor.

    Hoy devuelve el mismo orden. Aquí puedes introducir reglas duras o IA opcional.
    """
    return step_ids
