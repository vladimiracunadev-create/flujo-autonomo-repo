from engine.action_registry import ACTION_REGISTRY, LazyActionRegistry


def test_known_action_resolves():
    fn = ACTION_REGISTRY.get("system.wait_seconds")
    assert callable(fn)


def test_unknown_action_returns_none():
    assert ACTION_REGISTRY.get("totally.unknown") is None


def test_keys_contains_built_in():
    keys = set(ACTION_REGISTRY.keys())
    assert "filesystem.list_directory" in keys
    assert "rules.evaluate" in keys


def test_lazy_registry_caches_resolution():
    reg = LazyActionRegistry({"system.wait_seconds": "actions.system:wait_seconds"})
    a = reg.get("system.wait_seconds")
    b = reg.get("system.wait_seconds")
    assert a is b
