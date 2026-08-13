from importlib import import_module
from pathlib import Path


def test_active_main_entrypoint_imports_without_duplicate_api_module():
    active_main = import_module("main")

    assert active_main.app is not None
    assert not (Path(active_main.__file__).parent / "api" / "main.py").exists()
