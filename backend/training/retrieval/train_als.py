import pandas as pd
from pathlib import Path
from common.logger import get_logger
from common.config import config
from retrieval.models.als import ALSBuilder

log = get_logger(__name__)

def train_als_model():
    """
    Orchestrates the training and saving of the ALS model and its artifacts.
    """
    log.info("Starting ALS model training process...")
    
    # Ensure output directory for models and FAISS indices exists
    output_model_dir = Path(config.system.retrieval_artifacts.als.model_dir)
    output_model_dir.mkdir(parents=True, exist_ok=True)
    
    output_faiss_path = Path(config.system.retrieval_artifacts.als.faiss_index_path)
    output_faiss_path.parent.mkdir(parents=True, exist_ok=True)

    als_builder = ALSBuilder(
        ratings_path=Path(config.system.ratings_path),
        output_dir=output_model_dir
    )
    als_builder.build_and_save()
    
    log.info("ALS model training process completed successfully.")

if __name__ == "__main__":
    train_als_model()
