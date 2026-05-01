from __future__ import annotations

import re
from typing import Any


def get_path(data: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = data
    for part in path.split('.'):
        if isinstance(current, dict):
            current = current.get(part, default)
        else:
            return default
    return current


def matches(actual: Any, operator: str, expected: Any = None) -> bool:
    if operator == 'eq':
        return actual == expected
    if operator == 'ne':
        return actual != expected
    if operator == 'gt':
        return actual is not None and actual > expected
    if operator == 'gte':
        return actual is not None and actual >= expected
    if operator == 'lt':
        return actual is not None and actual < expected
    if operator == 'lte':
        return actual is not None and actual <= expected
    if operator == 'contains':
        return actual is not None and str(expected).lower() in str(actual).lower()
    if operator == 'in':
        return actual in expected if isinstance(expected, list) else False
    if operator == 'exists':
        return actual is not None
    if operator == 'not_exists':
        return actual is None
    if operator == 'truthy':
        return bool(actual)
    if operator == 'falsy':
        return not bool(actual)
    if operator == 'regex':
        return actual is not None and re.search(str(expected), str(actual)) is not None
    raise ValueError(f'Operador no soportado: {operator}')


def evaluate_condition(condition: dict[str, Any] | None, context: dict[str, Any]) -> bool:
    if not condition:
        return True
    if 'all' in condition:
        return all(evaluate_condition(item, context) for item in condition['all'])
    if 'any' in condition:
        return any(evaluate_condition(item, context) for item in condition['any'])
    if 'not' in condition:
        return not evaluate_condition(condition['not'], context)

    path = condition.get('path')
    operator = condition.get('operator', 'eq')
    expected = condition.get('value')
    actual = get_path(context, path, None) if path else None
    return matches(actual, operator, expected)
