from typing import TypedDict


class CandidateFeatureRow(TypedDict):
    # -------------------------
    # Identifiers
    # -------------------------
    user_id: int
    item_id: int

    # -------------------------
    # Retriever presence flags
    # -------------------------
    retrieved_by_two_tower: int
    retrieved_by_item_item: int
    retrieved_by_meta: int
    retrieved_by_content: int

    # -------------------------
    # Retriever scores
    # -------------------------
    two_tower_score: float
    item_item_score: float
    meta_score: float
    content_score: float

    # -------------------------
    # Retriever ranks
    # -------------------------
    two_tower_rank: int
    item_item_rank: int
    meta_rank: int
    content_rank: int

    # -------------------------
    # Cross-retriever aggregation
    # -------------------------
    num_retrievers: int

    # -------------------------
    # Item metadata / bias
    # -------------------------
    avg_rating: float
    num_ratings: int
    log_num_ratings: float
    release_year: int
    is_long_tail: int

    # -------------------------
    # User behavior aggregates
    # -------------------------
    user_num_interactions: int
    user_genre_diversity: float

    # -------------------------
    # Interaction features
    # -------------------------
    genre_overlap_ratio: float

    # -------------------------
    # Label (graded relevance)
    # -------------------------
    label: int
