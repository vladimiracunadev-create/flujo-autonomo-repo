from datetime import datetime, timezone

import pytest

from engine.cron import CronExpressionError, next_after, parse_cron, validate


def test_parse_basic_star():
    fields = parse_cron("* * * * *")
    assert fields[0].values[0] == 0
    assert fields[1].values[-1] == 23


def test_parse_step_and_range():
    fields = parse_cron("*/15 9-17 * * *")
    assert fields[0].values == [0, 15, 30, 45]
    assert fields[1].values == list(range(9, 18))


def test_parse_invalid_field_count():
    with pytest.raises(CronExpressionError):
        parse_cron("* * * *")


def test_parse_invalid_range():
    with pytest.raises(CronExpressionError):
        parse_cron("60 * * * *")


def test_validate_returns_none_on_valid():
    assert validate("0 0 * * *") is None
    assert validate("not a cron") is not None


def test_next_after_every_minute():
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    nxt = next_after("* * * * *", base)
    assert nxt == datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc)


def test_next_after_every_quarter_hour():
    base = datetime(2024, 1, 1, 12, 7, 30, tzinfo=timezone.utc)
    nxt = next_after("*/15 * * * *", base)
    assert nxt == datetime(2024, 1, 1, 12, 15, tzinfo=timezone.utc)


def test_next_after_specific_dow():
    # 0=lunes, 4=viernes; 2024-01-01 fue lunes
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    nxt = next_after("0 9 * * 4", base)  # próximo viernes 09:00
    assert nxt == datetime(2024, 1, 5, 9, 0, tzinfo=timezone.utc)


def test_next_after_daily_specific_time():
    base = datetime(2024, 6, 15, 23, 30, tzinfo=timezone.utc)
    nxt = next_after("0 6 * * *", base)
    assert nxt == datetime(2024, 6, 16, 6, 0, tzinfo=timezone.utc)
