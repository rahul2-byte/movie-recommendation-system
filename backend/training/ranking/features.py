"""Pure feature construction for the new leakage-safe ranking pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from data_pipeline.manifests import write_json


@dataclass(frozen=True)
class FeatureSchema:
    """Versioned ordered feature names shared by training and serving."""

    schema_version: str
    feature_names: tuple[str, ...]


def build_feature_schema(
    schema_version: str, feature_names: tuple[str, ...]
) -> FeatureSchema:
    """Create an explicit feature order shared by training and serving."""
    if (
        not schema_version
        or not feature_names
        or len(set(feature_names)) != len(feature_names)
    ):
        raise ValueError("Feature schema requires a version and unique feature names")
    return FeatureSchema(schema_version, feature_names)


def build_feature_frame(
    candidates: pd.DataFrame,
    train_interaction_counts: pd.Series,
    schema: FeatureSchema,
) -> pd.DataFrame:
    """Build finite, ordered features using only candidate and inner-train data."""
    # Column order is part of the LightGBM contract. The persisted schema and
    # serving loader must agree before this matrix can be used for inference.
    required = {"query_index", "candidate_tmdb_id", "label"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"Candidate rows are missing columns: {sorted(missing)}")
    output = candidates.loc[:, ["query_index", "candidate_tmdb_id", "label"]].copy()
    popularity = train_interaction_counts.astype(np.float32)

    def column_or_zeros(name: str) -> pd.Series:
        """Return a feature column or explicit zero evidence when absent."""
        # Missing retrieval evidence means this source did not return the
        # candidate; zero represents absence rather than an imputed score.
        return candidates.get(name, pd.Series(0, index=candidates.index))

    for name in schema.feature_names:
        if name.endswith("_score_normalized"):
            rank_name = name.removesuffix("_score_normalized") + "_rank"
            ranks = pd.to_numeric(column_or_zeros(rank_name), errors="coerce").fillna(0)
            output[name] = np.divide(
                1.0,
                ranks,
                out=np.zeros(len(ranks), dtype=np.float32),
                where=ranks.to_numpy() > 0,
            )
        elif name == "candidate_train_interaction_count":
            output[name] = (
                output["candidate_tmdb_id"].map(popularity).fillna(0).astype(np.float32)
            )
        elif name == "candidate_train_log_interaction_count":
            counts = output["candidate_tmdb_id"].map(popularity).fillna(0)
            output[name] = np.log1p(counts).astype(np.float32)
        else:
            output[name] = (
                pd.to_numeric(column_or_zeros(name), errors="coerce")
                .fillna(0)
                .astype(np.float32)
            )
    output.loc[:, schema.feature_names] = np.nan_to_num(
        output.loc[:, schema.feature_names].to_numpy(dtype=np.float32),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    return output


def write_feature_schema(
    path: Path,
    schema: FeatureSchema,
    dataset_version: str,
    config_sha256: str,
    code_sha256: str,
) -> None:
    """Persist the compatibility contract beside a generated feature dataset."""
    write_json(
        path,
        {
            "schema_version": schema.schema_version,
            "feature_names": list(schema.feature_names),
            "defaults": {name: 0.0 for name in schema.feature_names},
            "dataset_version": dataset_version,
            "config_sha256": config_sha256,
            "code_sha256": code_sha256,
        },
    )
