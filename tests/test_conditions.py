from engine.conditions import evaluate_condition, get_path, matches


def test_get_path_dotted():
    assert get_path({"a": {"b": 5}}, "a.b") == 5
    assert get_path({"a": 1}, "a.b") is None


def test_matches_basic_operators():
    assert matches(5, "gt", 3) is True
    assert matches(5, "lte", 5) is True
    assert matches("hola mundo", "contains", "MUNDO") is True
    assert matches(None, "exists") is False
    assert matches(None, "not_exists") is True
    assert matches("a-1", "regex", r"^a-\d$") is True


def test_evaluate_condition_all_any_not():
    ctx = {"x": 10, "y": "ok"}
    assert evaluate_condition({"path": "x", "operator": "eq", "value": 10}, ctx)
    assert evaluate_condition({"all": [
        {"path": "x", "operator": "gt", "value": 5},
        {"path": "y", "operator": "eq", "value": "ok"},
    ]}, ctx)
    assert not evaluate_condition({"any": [
        {"path": "x", "operator": "lt", "value": 0},
        {"path": "y", "operator": "eq", "value": "no"},
    ]}, ctx)
    assert evaluate_condition({"not": {"path": "y", "operator": "eq", "value": "no"}}, ctx)


def test_evaluate_condition_none_is_true():
    assert evaluate_condition(None, {}) is True
