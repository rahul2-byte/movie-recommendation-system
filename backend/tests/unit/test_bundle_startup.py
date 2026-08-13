import os

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import main


def test_startup_validates_configured_bundle_before_serving(monkeypatch):
    calls = []
    monkeypatch.setattr(main.config.settings, "MODEL_BUNDLE_DIR", "/models")
    monkeypatch.setattr(
        main, "get_pipeline", lambda: calls.append("bundle"), raising=False
    )
    monkeypatch.setattr(main, "start_background_tasks", lambda: calls.append("tasks"))

    main.startup()

    assert calls == ["bundle", "tasks"]
