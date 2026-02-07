import pandas as pd
from pathlib import Path
from common.logger import get_logger
from common.config import config
from retrieval.models.als import ALSBuilder
from tracking.mlflow_client import MlflowClient

log = get_logger(__name__)

def train_als_model():
    """
    Orchestrates the training and saving of the ALS model and its artifacts.
    Logs process to MLflow.
    """
    log.info("Starting ALS model training process...")
    
    # Ensure output directory for models and FAISS indices exists
    output_model_dir = Path(config.system.retrieval_artifacts.als.model_dir)
    output_model_dir.mkdir(parents=True, exist_ok=True)
    
    output_faiss_path = Path(config.system.retrieval_artifacts.als.faiss_index_path)
    output_faiss_path.parent.mkdir(parents=True, exist_ok=True)

    # Setup MLflow
    mlflow_client = MlflowClient(
        experiment_name=config.system.tracking.retrieval_experiment_name,
        tracking_uri=config.settings.MLFLOW_TRACKING_URI
    )

    with mlflow_client.start_run(run_name="als_training") as run:
        log.info(f"MLflow Run ID: {run.info.run_id}")
        mlflow_client.log_params({
            "model_type": "ALS",
            "ratings_path": config.system.ratings_path,
            "output_dir": str(output_model_dir)
        })

        als_builder = ALSBuilder(
            ratings_path=Path(config.system.ratings_path),
            output_dir=output_model_dir
        )
        als_builder.build_and_save()
        
        log.info("ALS model training process completed successfully.")

if __name__ == "__main__":
    train_als_model()