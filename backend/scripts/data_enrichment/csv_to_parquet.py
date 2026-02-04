from pathlib import Path
import pandas as pd

from validate import load_schema, validate_dataframe_schema


def convert_csv_to_parquet(
    *,
    csv_path: Path,
    parquet_path: Path,
    schema_path: Path,
    drop_null_cols: list[str] | None = None,
) -> None:
    df = pd.read_csv(csv_path)

    if drop_null_cols:
        before = len(df)
        df = df.dropna(subset=drop_null_cols)
        after = len(df)

        print(
            f"Dropped {before - after} rows due to nulls in {drop_null_cols}"
        )

    schema = load_schema(schema_path)
    validate_dataframe_schema(df, schema)

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, index=False)

    print(
        f"Converted {csv_path.name} → {parquet_path.name} "
        f"| rows={len(df)}"
    )



def main() -> None:
    # Define paths relative to the project root to make script executable from anywhere
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    base_csv = PROJECT_ROOT / "data/raw"
    base_parquet = PROJECT_ROOT / "data/processed"
    schema_dir = PROJECT_ROOT / "configs/schemas"

    convert_csv_to_parquet(
        csv_path=base_csv / "movies.csv",
        parquet_path=base_parquet / "movies.parquet",
        schema_path=schema_dir / "movielens_movies.yaml",
    )

    convert_csv_to_parquet(
        csv_path=base_csv / "links.csv",
        parquet_path=base_parquet / "links.parquet",
        schema_path=schema_dir / "movielens_links.yaml",
        drop_null_cols=["tmdbId"]
    )

    convert_csv_to_parquet(
        csv_path=base_csv / "tags.csv",
        parquet_path=base_parquet / "tags.parquet",
        schema_path=schema_dir / "movielens_tags.yaml",
    )

    convert_csv_to_parquet(
        csv_path=base_csv / "ratings.csv",
        parquet_path=base_parquet / "ratings.parquet",
        schema_path=schema_dir / "movielens_ratings.yaml",
    )


if __name__ == "__main__":
    main()
