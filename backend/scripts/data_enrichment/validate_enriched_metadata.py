"""Validate enriched metadata against the checked-in schema definition."""

from pathlib import Path

import pandas as pd
import yaml


def load_schema(schema_path: Path) -> dict:
    """Load one YAML schema definition from disk."""
    with open(schema_path) as f:
        return yaml.safe_load(f)["columns"]


def validate_dataframe_schema(
    df: pd.DataFrame,
    schema: dict,
) -> None:
    """Raise a descriptive error when dataframe columns or dtypes mismatch."""
    expected_cols = set(schema.keys())
    actual_cols = set(df.columns)

    if expected_cols != actual_cols:
        raise ValueError(
            f"Schema mismatch\nExpected: {expected_cols}\nActual: {actual_cols}"
        )

    for col, dtype in schema.items():
        try:
            df[col] = df[col].astype(dtype)
        except Exception as exc:
            raise TypeError(f"Failed casting column '{col}' to {dtype}") from exc
