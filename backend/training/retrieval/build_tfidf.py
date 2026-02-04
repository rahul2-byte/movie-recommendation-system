from pathlib import Path

import pandas as pd
from common.config import config
from common.logger import get_logger
from retrieval.models.tfidf import TFIDFBuilder

log = get_logger(__name__)


def build_tfidf_model():
    """
    Orchestrates the building and saving of the TF-IDF model and its artifacts.
    """
    log.info("Starting TF-IDF model building process...")

    # Ensure output directory exists
    output_dir = Path(config.system.retrieval_artifacts.tfidf.model_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tfidf_builder = TFIDFBuilder(
        movies_metadata_path=Path(config.system.movies_metadata_path),
        output_dir=output_dir,
    )
    tfidf_builder.build_and_save()

    log.info("TF-IDF model building process completed successfully.")


if __name__ == "__main__":
    build_tfidf_model()
