import pandas as pd
from pathlib import Path
from common.logger import get_logger
from common.config import config
from configs.settings import TOP_N_TAGS
from retrieval.models.two_tower import TwoTowerBuilder
from tracking.mlflow_client import MlflowClient

log = get_logger(__name__)

def train_two_tower_model():
    """
    Orchestrates the training and saving of the Two-Tower model and its artifacts.
    Logs to MLflow.
    """
    log.info("Starting Two-Tower model training process...")
    
    # Ensure output directory for models and FAISS indices exists
    two_tower_model_dir = Path(config.system.retrieval_artifacts.two_tower.model_dir)
    two_tower_model_dir.mkdir(parents=True, exist_ok=True)
    two_tower_faiss_path = Path(config.system.retrieval_artifacts.two_tower.faiss_index_path)
    two_tower_faiss_path.parent.mkdir(parents=True, exist_ok=True)

    # Setup MLflow
    mlflow_client = MlflowClient(
        experiment_name=config.system.tracking.retrieval_experiment_name,
        tracking_uri=config.settings.MLFLOW_TRACKING_URI
    )

    with mlflow_client.start_run(run_name="two_tower_training") as run:
        log.info(f"MLflow Run ID: {run.info.run_id}")
        
        two_tower_cfg = config.retrieval.two_tower
        params = {
            "model_type": "TwoTower",
            "embedding_dim": int(two_tower_cfg.get("embedding_dim", 64)),
            "epochs": int(two_tower_cfg.get("epochs", 5)),
            "batch_size": int(two_tower_cfg.get("batch_size", 256)),
            "learning_rate": float(two_tower_cfg.get("learning_rate", 1e-3)),
            "num_negatives": int(two_tower_cfg.get("num_negatives", 5)),
            "top_n_tags": TOP_N_TAGS,
            "sequences_path": config.system.training_sequences_path
        }
        mlflow_client.log_params(params)

        builder = TwoTowerBuilder(
            sequences_path=Path(config.system.training_sequences_path),
            movies_metadata_path=Path(config.system.movies_metadata_path),
            tags_path=Path(config.system.tags_path),
            output_dir=two_tower_model_dir,
            embedding_dim=params["embedding_dim"],
            epochs=params["epochs"],
            batch_size=params["batch_size"],
            learning_rate=params["learning_rate"],
            num_negatives=params["num_negatives"],
            top_n_tags=params["top_n_tags"]
        )
        builder.build_and_save()
        
        log.info("Two-Tower model training process completed successfully.")

if __name__ == "__main__":
    train_two_tower_model()