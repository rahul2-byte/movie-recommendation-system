from pathlib import Path
import yaml
import pandas as pd


def load_schema(schema_path: Path) -> dict:
    with open(schema_path, "r") as f:
        return yaml.safe_load(f)["columns"]


def validate_dataframe_schema(
    df: pd.DataFrame,
    schema: dict,
) -> None:
    expected_cols = set(schema.keys())
    actual_cols = set(df.columns)

    if expected_cols != actual_cols:
        raise ValueError(
            f"Schema mismatch\n"
            f"Expected: {expected_cols}\n"
            f"Actual: {actual_cols}"
        )

    for col, dtype in schema.items():
        try:
            df[col] = df[col].astype(dtype)
        except Exception as exc:
            raise TypeError(
                f"Failed casting column '{col}' to {dtype}"
            ) from exc
