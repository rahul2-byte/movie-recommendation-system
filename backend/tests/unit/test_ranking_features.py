from __future__ import annotations

import json

import numpy as np
import pandas as pd
from data_pipeline.config import load_ranking_features_config
from training.ranking.features import (
    build_feature_frame,
    build_feature_schema,
    write_feature_schema,
)


def test_ranking_feature_config_declares_ordered_schema(tmp_path):
    path = tmp_path / "ranking_features.yaml"
    path.write_text(
        """
schema_version: ranking-features-v1
compression: zstd
compression_level: 3
features:
  - retrieval_source_count
  - retrieval_als_rank
  - retrieval_als_score_normalized
  - candidate_train_interaction_count
  - candidate_train_log_interaction_count
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_ranking_features_config(path)

    assert config.schema_version == "ranking-features-v1"
    assert config.feature_names[-1] == "candidate_train_log_interaction_count"


def test_feature_frame_has_stable_order_and_train_only_popularity():
    schema = build_feature_schema(
        "ranking-features-v1",
        (
            "retrieval_source_count",
            "retrieval_als_rank",
            "retrieval_als_score_normalized",
            "retrieval_item_graph_rank",
            "retrieval_item_graph_score_normalized",
            "retrieval_two_tower_rank",
            "retrieval_two_tower_score_normalized",
            "candidate_train_interaction_count",
            "candidate_train_log_interaction_count",
        ),
    )
    candidates = pd.DataFrame(
        {
            "query_index": [0, 0],
            "candidate_tmdb_id": [10, 20],
            "label": [1, 0],
            "retrieval_source_count": [2, 1],
            "retrieval_als_rank": [1, 0],
            "retrieval_item_graph_rank": [10, 2],
        }
    )

    features = build_feature_frame(
        candidates,
        pd.Series({10: 7}, name="candidate_train_interaction_count"),
        schema,
    )

    assert list(features.columns) == [
        "query_index",
        "candidate_tmdb_id",
        "label",
        *schema.feature_names,
    ]
    assert "user_id" not in features
    assert np.isclose(features.loc[0, "retrieval_als_score_normalized"], 1.0)
    assert np.isclose(features.loc[0, "retrieval_item_graph_score_normalized"], 0.1)
    assert np.isclose(features.loc[1, "retrieval_als_score_normalized"], 0.0)
    assert np.isclose(features.loc[0, "retrieval_two_tower_rank"], 0.0)
    assert features.loc[1, "candidate_train_interaction_count"] == 0.0
    assert np.isfinite(features.loc[:, schema.feature_names].to_numpy()).all()


def test_feature_schema_records_order_defaults_and_provenance(tmp_path):
    schema = build_feature_schema("ranking-features-v1", ("retrieval_als_rank",))
    path = tmp_path / "feature_schema.json"

    write_feature_schema(path, schema, "dataset-v1", "config-sha", "code-sha")

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "schema_version": "ranking-features-v1",
        "feature_names": ["retrieval_als_rank"],
        "defaults": {"retrieval_als_rank": 0.0},
        "dataset_version": "dataset-v1",
        "config_sha256": "config-sha",
        "code_sha256": "code-sha",
    }
