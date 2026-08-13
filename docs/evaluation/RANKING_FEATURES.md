# Ranking feature contract

The ranker consumes the features below in the exact order declared by
`backend/configs/ranking_features.yaml`. Training and serving must use the same
schema version and defaults.

| Feature | Type | Source / transformation | Missing value |
| --- | --- | --- | --- |
| `retrieval_source_count` | float | Number of retrievers returning the candidate | `0` |
| `retrieval_als_rank` | float | ALS rank; lower is better | `0` |
| `retrieval_als_score_normalized` | float | `1 / retrieval_als_rank` | `0` |
| `retrieval_item_graph_rank` | float | Item-graph rank; lower is better | `0` |
| `retrieval_item_graph_score_normalized` | float | `1 / retrieval_item_graph_rank` | `0` |
| `retrieval_two_tower_rank` | float | Two-tower rank; lower is better | `0` |
| `retrieval_two_tower_score_normalized` | float | `1 / retrieval_two_tower_rank` | `0` |
| `retrieval_content_rank` | float | Metadata/content rank; lower is better | `0` |
| `retrieval_content_score_normalized` | float | `1 / retrieval_content_rank` | `0` |
| `candidate_train_interaction_count` | float | Positive interactions for the candidate in inner training data | `0` |
| `candidate_train_log_interaction_count` | float | `log1p(candidate_train_interaction_count)` | `0` |

The normalized score names are rank-derived reciprocal scores, not raw model
similarities. This keeps source values comparable during fusion. A candidate
missing from one retriever receives zero for that source's rank and score.

Feature order is a compatibility contract: changing it requires a new schema
version, retraining the ranker, rebuilding the model bundle, and rerunning the
validation and test gates.
