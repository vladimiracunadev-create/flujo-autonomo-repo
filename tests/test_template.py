from engine.template import flatten_context, render_value


def test_flatten_context_nested():
    flat = flatten_context({"a": {"b": 1, "c": {"d": 2}}})
    assert flat["a.b"] == 1
    assert flat["a.c.d"] == 2


def test_render_string_substitutes_placeholder():
    out = render_value("hola {name}", {"name": "mundo"})
    assert out == "hola mundo"


def test_render_exact_placeholder_returns_value_with_type():
    """Un placeholder exacto debe preservar el tipo (dict, list, etc)."""
    payload = {"foo": [1, 2, 3]}
    out = render_value("{{ data }}", {"data": payload})
    # El motor traduce {{x}} -> {x} antes de resolver
    assert out == payload


def test_render_missing_key_keeps_placeholder():
    out = render_value("{missing}", {})
    assert out == "{missing}"


def test_render_recurses_dict_and_list():
    rendered = render_value(
        {"path": "/x/{name}", "items": ["{name}", 7]},
        {"name": "abc"},
    )
    assert rendered == {"path": "/x/abc", "items": ["abc", 7]}


def test_render_now_placeholder_present():
    out = render_value("snap_{now}.json", {})
    assert out.startswith("snap_") and out.endswith(".json")
    assert len(out) > len("snap_.json")
