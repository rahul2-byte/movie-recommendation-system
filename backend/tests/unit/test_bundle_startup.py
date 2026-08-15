import os

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import main


def test_startup_validates_configured_bundle_before_serving(monkeypatch):
    calls = []
    monkeypatch.setattr(main.settings, "MODEL_BUNDLE_DIR", "/models")
    monkeypatch.setattr(
        main, "get_pipeline", lambda: calls.append("bundle"), raising=False
    )
    main.startup()

    assert calls == ["bundle"]
