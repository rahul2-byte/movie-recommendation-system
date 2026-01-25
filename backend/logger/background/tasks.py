# background/tasks.py
from logger.services.mlflow_logger import flush_to_mlflow

def start_background_tasks():
    import threading
    import time

    def runner():
        while True:
            flush_to_mlflow()
            time.sleep(60)  # every 1 min

    threading.Thread(daemon=True, target=runner).start()
