# api/recommend/feature_schema.py
FEATURE_NAMES = [
    "query_id",
    "retrieved_by_two_tower",
    "retrieved_by_als",
    "retrieved_by_item_cf",
    "retrieved_by_content",
    "two_tower_score",
    "als_score",
    "item_cf_score",
    "content_score",
    "num_retrievers",
]
