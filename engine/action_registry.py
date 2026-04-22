from __future__ import annotations

from importlib import import_module
from typing import Callable, Dict, Iterable, Optional

ActionFn = Callable[..., dict]


class LazyActionRegistry:
    """Resolve action functions only when a flow actually uses them."""

    def __init__(self, action_paths: Dict[str, str]) -> None:
        self._action_paths = action_paths
        self._cache: Dict[str, ActionFn] = {}

    def get(self, action_name: str) -> Optional[ActionFn]:
        if action_name not in self._action_paths:
            return None
        if action_name not in self._cache:
            module_name, function_name = self._action_paths[action_name].split(':', 1)
            module = import_module(module_name)
            self._cache[action_name] = getattr(module, function_name)
        return self._cache[action_name]

    def keys(self) -> Iterable[str]:
        return self._action_paths.keys()


ACTION_REGISTRY = LazyActionRegistry(
    {
        'filesystem.ensure_directory': 'actions.filesystem:ensure_directory',
        'filesystem.list_directory': 'actions.filesystem:list_directory',
        'filesystem.write_json': 'actions.filesystem:write_json',
        'filesystem.read_text_file': 'actions.filesystem:read_text_file',
        'filesystem.classify_file_inventory': 'actions.filesystem:classify_file_inventory',
        'filesystem.summarize_text_folder': 'actions.filesystem:summarize_text_folder',
        'filesystem.move_file': 'actions.filesystem:move_file',
        'screen.capture_screenshot': 'actions.screen:capture_screenshot',
        'vision.analyze_image': 'actions.vision:analyze_image',
        'vision.ocr_image': 'actions.vision:ocr_image',
        'vision.find_text_in_image': 'actions.vision:find_text_in_image',
        'vision.select_image': 'actions.vision:select_image',
        'vision.inspect_screen_target': 'actions.vision:inspect_screen_target',
        'system.wait_seconds': 'actions.system:wait_seconds',
        'system.snapshot_system': 'actions.system:snapshot_system',
        'system.top_processes': 'actions.system:top_processes',
        'system.watch_processes': 'actions.system:watch_processes',
        'rules.evaluate': 'actions.rules:evaluate_rules',
        'ui.open_url': 'actions.ui:open_url',
        'ui.open_file_in_browser': 'actions.ui:open_file_in_browser',
        'ui.launch_process': 'actions.ui:launch_process',
        'ui.hotkey': 'actions.ui:hotkey',
        'ui.type_text': 'actions.ui:type_text',
        'ui.click': 'actions.ui:click',
        'ui.click_bbox': 'actions.ui:click_bbox',
        'http.fetch_url': 'actions.http_actions:fetch_url',
    }
)
