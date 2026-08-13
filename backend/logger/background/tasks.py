"""Optional background telemetry flush task for the API process."""

from logger.services.mlflow_logger import flush_to_mlflow


def start_background_tasks():
    """Start periodic MLflow flushing without blocking request handling."""
    import threading
    import time

    def runner():
        """Flush buffered telemetry at a low-frequency background interval."""
        while True:
            flush_to_mlflow()
            time.sleep(60)  # every 1 min

    threading.Thread(daemon=True, target=runner).start()
