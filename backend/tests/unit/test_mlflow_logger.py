import importlib
import sys
from contextlib import nullcontext
from types import SimpleNamespace

import mlflow


def _fresh_logger():
    sys.modules.pop("logger.services.mlflow_logger", None)
    sys.modules.pop("logger.services.mlflow_utils", None)
    return importlib.import_module("logger.services.mlflow_logger")


def _reset_buffers(logger):
    logger.REQUEST_BUFFER.clear()
    logger.METRIC_BUFFER["latency_ms"].clear()
    logger.METRIC_BUFFER["clicked"] = 0
    logger.METRIC_BUFFER["impressions"] = 0


def test_importing_main_does_not_configure_mlflow(monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise RuntimeError("MLflow is unavailable")

    monkeypatch.setattr(mlflow, "set_tracking_uri", fail)
    monkeypatch.setattr(mlflow, "get_experiment_by_name", fail)
    monkeypatch.setattr(mlflow, "create_experiment", fail)
    for module in (
        "main",
        "api.v1.recommend",
        "logger.services.mlflow_logger",
        "logger.services.mlflow_utils",
    ):
        sys.modules.pop(module, None)

    importlib.import_module("main")

    assert calls == []


def test_logging_hooks_keep_telemetry_in_memory_when_mlflow_setup_fails(monkeypatch):
    monkeypatch.setattr(
        mlflow,
        "set_tracking_uri",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    logger = _fresh_logger()
    _reset_buffers(logger)

    logger.log_recommendation({"request_id": "request-1"}, 17)
    logger.log_click()

    assert logger.REQUEST_BUFFER == [{"request_id": "request-1"}]
    assert logger.METRIC_BUFFER == {
        "latency_ms": [17],
        "clicked": 1,
        "impressions": 1,
    }


def test_failed_flush_preserves_buffered_telemetry(monkeypatch):
    monkeypatch.setattr(mlflow, "set_tracking_uri", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        mlflow,
        "get_experiment_by_name",
        lambda *args, **kwargs: SimpleNamespace(experiment_id="1"),
    )
    logger = _fresh_logger()
    _reset_buffers(logger)
    logger.log_recommendation({"request_id": "request-1"}, 17)
    monkeypatch.setattr(
        mlflow,
        "start_run",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )

    logger.flush_to_mlflow()

    assert logger.REQUEST_BUFFER == [{"request_id": "request-1"}]
    assert logger.METRIC_BUFFER["latency_ms"] == [17]


def test_successful_flush_clears_buffers(monkeypatch):
    monkeypatch.setattr(mlflow, "set_tracking_uri", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        mlflow,
        "get_experiment_by_name",
        lambda *args, **kwargs: SimpleNamespace(experiment_id="1"),
    )
    logger = _fresh_logger()
    _reset_buffers(logger)
    for name in ("set_tag", "log_param", "log_metric", "log_dict"):
        monkeypatch.setattr(mlflow, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(mlflow, "start_run", lambda *args, **kwargs: nullcontext())
    logger.log_recommendation({"request_id": "request-1"}, 17)
    logger.log_click()

    logger.flush_to_mlflow()

    assert logger.REQUEST_BUFFER == []
    assert logger.METRIC_BUFFER == {"latency_ms": [], "clicked": 0, "impressions": 0}
