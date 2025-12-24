from typing import TypedDict


class CandidateFeatureRow(TypedDict):
    user_id: int
    item_id: int

    retrieved_by_two_tower: int
    retrieved_by_als: int
    retrieved_by_item_item: int
    retrieved_by_content: int

    two_tower_score: float
    two_tower_rank: int
    als_score: float
    als_rank: int
    item_item_score: float
    item_item_rank: int
    content_score: float
    content_rank: int

    num_retrievers: int

    label: int
