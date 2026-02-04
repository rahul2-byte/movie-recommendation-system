from pathlib import Path

import pandas as pd
from common.config import config
from common.logger import get_logger
from retrieval.models.content_based import ContentBasedBuilder

log = get_logger(__name__)


def build_content_model():
    """
    Orchestrates the building and saving of the Content-Based model and its artifacts.
    """
    log.info("Starting Content-Based model building process...")

    # Ensure output directory for models and FAISS indices exists
    output_model_dir = Path(config.system.retrieval_artifacts.content_based.model_dir)
    output_model_dir.mkdir(parents=True, exist_ok=True)

    output_faiss_path = Path(
        config.system.retrieval_artifacts.content_based.faiss_index_path
    )
    output_faiss_path.parent.mkdir(parents=True, exist_ok=True)

    content_builder = ContentBasedBuilder(
        movies_metadata_path=Path(config.system.movies_metadata_path),
        tags_path=Path(config.system.tags_path),
        output_dir=output_model_dir,
    )
    content_builder.build_and_save()

    log.info("Content-Based model building process completed successfully.")


if __name__ == "__main__":
    build_content_model()
