"""Typed configuration for the offline data pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when data-pipeline configuration is invalid."""


def _mapping(value: Any, name: str) -> dict[str, Any]:
    """Require a YAML section to be a mapping before reading its fields."""
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _path(config_dir: Path, value: Any, name: str) -> Path:
    """Resolve a required config path relative to its YAML file."""
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{name} must be a non-empty path")
    return (config_dir / value).resolve()


@dataclass(frozen=True)
class DatasetConfig:
    """Input locations and schema identity for one dataset version."""
    name: str
    schema_version: str
    raw_dir: Path
    enriched_metadata_path: Path
    versions_dir: Path


@dataclass(frozen=True)
class PrepareConfig:
    """Compression and bucketing controls for preparation outputs."""
    compression: str
    compression_level: int
    user_bucket_count: int


@dataclass(frozen=True)
class SplitConfig:
    """Temporal split rules that define train/validation/test boundaries."""
    strategy: str
    train_fraction: float
    validation_fraction: float
    positive_rating_threshold: float
    min_positive_interactions: int
    min_train_interactions: int
    seed_count: int

    @property
    def test_fraction(self) -> float:
        """Return the fraction left for the test partition."""
        return 1.0 - self.train_fraction - self.validation_fraction


@dataclass(frozen=True)
class DataPipelineConfig:
    """Fully resolved, validated configuration for offline data processing."""
    path: Path
    dataset: DatasetConfig
    prepare: PrepareConfig
    split: SplitConfig
    raw: dict[str, Any]

    def version_payload(self) -> dict[str, Any]:
        """Return path-normalized config data used in dataset fingerprints."""
        payload = asdict(self)
        payload.pop("path", None)
        for section in payload.values():
            if isinstance(section, dict):
                for key, value in list(section.items()):
                    if isinstance(value, Path):
                        section[key] = str(value)
        return payload


def load_config(path: Path) -> DataPipelineConfig:
    """Load YAML and reject settings that cannot produce a valid split."""
    path = path.resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid YAML in {path}: {error}") from error
    raw = _mapping(raw, "configuration")
    config_dir = path.parent
    dataset = _mapping(raw.get("dataset"), "dataset")
    prepare = _mapping(raw.get("prepare"), "prepare")
    split = _mapping(raw.get("split"), "split")
    dataset_config = DatasetConfig(
        name=str(dataset.get("name", "")),
        schema_version=str(dataset.get("schema_version", "")),
        raw_dir=_path(config_dir, dataset.get("raw_dir"), "dataset.raw_dir"),
        enriched_metadata_path=_path(
            config_dir,
            dataset.get("enriched_metadata_path"),
            "dataset.enriched_metadata_path",
        ),
        versions_dir=_path(
            config_dir, dataset.get("versions_dir"), "dataset.versions_dir"
        ),
    )
    if not dataset_config.name or not dataset_config.schema_version:
        raise ConfigError("dataset.name and dataset.schema_version are required")
    prepare_config = PrepareConfig(
        compression=str(prepare.get("compression", "")),
        compression_level=int(prepare.get("compression_level", 0)),
        user_bucket_count=int(prepare.get("user_bucket_count", 0)),
    )
    if prepare_config.compression != "zstd":
        raise ConfigError("prepare.compression must be zstd")
    if not 1 <= prepare_config.compression_level <= 22:
        raise ConfigError("prepare.compression_level must be between 1 and 22")
    if prepare_config.user_bucket_count < 1:
        raise ConfigError("prepare.user_bucket_count must be positive")
    split_config = SplitConfig(
        strategy=str(split.get("strategy", "per_user_chronological")),
        train_fraction=float(split.get("train_fraction", 0)),
        validation_fraction=float(split.get("validation_fraction", 0)),
        positive_rating_threshold=float(split.get("positive_rating_threshold", 0)),
        min_positive_interactions=int(split.get("min_positive_interactions", 0)),
        min_train_interactions=int(split.get("min_train_interactions", 0)),
        seed_count=int(split.get("seed_count", 0)),
    )
    if split_config.strategy not in {
        "per_user_chronological",
        "global_temporal_cutoffs",
    }:
        raise ConfigError(
            "split.strategy must be per_user_chronological or global_temporal_cutoffs"
        )
    if not 0.0 < split_config.train_fraction < 1.0:
        raise ConfigError("split.train_fraction must be between zero and one")
    if not 0.0 < split_config.validation_fraction < 1.0:
        raise ConfigError("split.validation_fraction must be between zero and one")
    if split_config.test_fraction <= 0.0:
        raise ConfigError("train_fraction + validation_fraction must be below one")
    if split_config.seed_count < 1:
        raise ConfigError("split.seed_count must be positive")
    if split_config.min_train_interactions < split_config.seed_count + 1:
        raise ConfigError("split.min_train_interactions must allow seeds and a target")
    if split_config.min_positive_interactions < split_config.min_train_interactions + 2:
        raise ConfigError(
            "split.min_positive_interactions must allow validation and test"
        )
    return DataPipelineConfig(path, dataset_config, prepare_config, split_config, raw)


@dataclass(frozen=True)
class RankingDataConfig:
    """Configuration for leakage-safe ranking-data generation."""

    path: Path
    dataset_version: str
    inner_train_fraction: float
    positive_rating_threshold: float
    seed_count: int
    candidate_k: int
    candidate_limit: int
    candidate_query_batch_size: int
    retrievers: tuple[str, ...]
    compression: str
    compression_level: int
    random_seed: int
    mlflow_experiment_name: str

    @property
    def minimum_events_per_user(self) -> int:
        """Five seeds and one strictly later target at a minimum."""
        return self.seed_count + 1


@dataclass(frozen=True)
class RankingFeaturesConfig:
    """Ordered, versioned feature contract for ranking data."""

    path: Path
    schema_version: str
    compression: str
    compression_level: int
    feature_names: tuple[str, ...]


def load_ranking_data_config(path: Path) -> RankingDataConfig:
    """Load and validate the ranking-data contract from YAML."""
    path = path.resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid YAML in {path}: {error}") from error
    raw = _mapping(raw, "ranking data configuration")
    tracking = _mapping(raw.get("tracking"), "tracking")
    retrievers = raw.get("retrievers")
    if not isinstance(retrievers, list) or not retrievers:
        raise ConfigError("retrievers must be a non-empty list")
    allowed_retrievers = {"als", "item_graph", "two_tower", "content"}
    if not set(retrievers).issubset(allowed_retrievers):
        raise ConfigError(
            "retrievers must contain only als, item_graph, two_tower, and content"
        )
    if len(set(retrievers)) != len(retrievers):
        raise ConfigError("retrievers must not contain duplicates")
    config = RankingDataConfig(
        path=path,
        dataset_version=str(raw.get("dataset_version", "")),
        inner_train_fraction=float(raw.get("inner_train_fraction", 0)),
        positive_rating_threshold=float(raw.get("positive_rating_threshold", 0)),
        seed_count=int(raw.get("seed_count", 0)),
        candidate_k=int(raw.get("candidate_k", 0)),
        candidate_limit=int(raw.get("candidate_limit", raw.get("candidate_k", 0))),
        candidate_query_batch_size=int(raw.get("candidate_query_batch_size", 1_000)),
        retrievers=tuple(str(retriever) for retriever in retrievers),
        compression=str(raw.get("compression", "")),
        compression_level=int(raw.get("compression_level", 0)),
        random_seed=int(raw.get("random_seed", 0)),
        mlflow_experiment_name=str(tracking.get("experiment_name", "")),
    )
    if not config.dataset_version:
        raise ConfigError("dataset_version is required")
    if not 0.0 < config.inner_train_fraction < 1.0:
        raise ConfigError("inner_train_fraction must be between zero and one")
    if config.positive_rating_threshold <= 0.0:
        raise ConfigError("positive_rating_threshold must be positive")
    if config.seed_count < 1:
        raise ConfigError("seed_count must be positive")
    if config.candidate_k < 1:
        raise ConfigError("candidate_k must be positive")
    if config.candidate_limit < 1:
        raise ConfigError("candidate_limit must be positive")
    if config.candidate_query_batch_size < 1:
        raise ConfigError("candidate_query_batch_size must be positive")
    if config.compression != "zstd":
        raise ConfigError("compression must be zstd")
    if not 1 <= config.compression_level <= 22:
        raise ConfigError("compression_level must be between 1 and 22")
    if not config.mlflow_experiment_name:
        raise ConfigError("tracking.experiment_name is required")
    return config


def load_ranking_features_config(path: Path) -> RankingFeaturesConfig:
    """Load the small, explicit feature schema used by the ranker."""
    path = path.resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid YAML in {path}: {error}") from error
    raw = _mapping(raw, "ranking feature configuration")
    names = raw.get("features")
    if (
        not isinstance(names, list)
        or not names
        or not all(isinstance(name, str) and name for name in names)
    ):
        raise ConfigError("features must be a non-empty list of names")
    if len(set(names)) != len(names):
        raise ConfigError("features must not contain duplicates")
    config = RankingFeaturesConfig(
        path=path,
        schema_version=str(raw.get("schema_version", "")),
        compression=str(raw.get("compression", "")),
        compression_level=int(raw.get("compression_level", 0)),
        feature_names=tuple(names),
    )
    if not config.schema_version:
        raise ConfigError("schema_version is required")
    if config.compression != "zstd":
        raise ConfigError("compression must be zstd")
    if not 1 <= config.compression_level <= 22:
        raise ConfigError("compression_level must be between 1 and 22")
    return config
