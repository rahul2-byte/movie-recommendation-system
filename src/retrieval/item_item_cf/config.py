from dataclasses import dataclass


@dataclass(frozen=True)
class ItemItemCFConfig:
    top_k_per_item: int = 500
    implicit_alpha: float = 40.0
    min_interactions_per_item: int = 5
    use_implicit: bool = True
    dtype: str = "float32"
