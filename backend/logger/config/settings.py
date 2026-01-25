# config/settings.py

MLFLOW_TRACKING_URI = "./backend/mlruns"
MLFLOW_EXPERIMENTS = {
    "offline": "recommender_offline_eval",
    "online": "recommender_online_inference",
}

TRACE_SAMPLE_SIZE = 2
