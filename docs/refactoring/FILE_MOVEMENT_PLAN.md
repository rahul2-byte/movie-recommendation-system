# File movement plan

The 2026-08 naming migration completed the repository-wide clean break.
Canonical imports now use `configuration`, `observability`, and
`infrastructure.clients`; the old `common`, `configs`, and `logger` paths do
not remain as forwarding modules.

## Canonical modules

- Runtime orchestration: `serving.recommendation_pipeline` and
  `serving.bundle_recommender`.
- Offline evaluation: `evaluation.offline_evaluator` and `evaluation.rank_fusion`.
- Ranking data: `data_pipeline.ranking_dataset`.
- Retrieval trainers: `als_trainer`, `content_retriever`, `item_graph_trainer`,
  and `two_tower_trainer`.
- Enrichment: `tmdb_omdb_normalization`, `movie_enrichment`, and the
  `enrichment_*` storage modules.

## Migration contract

Old Python import paths are intentionally unsupported. HTTP routes, CLI flags,
environment-variable names, artifact filenames, and model-bundle schemas were
not changed. Every future structural move must update consumers, Docker/CI,
documentation, and the module-naming contract test before removal of the old
path.
