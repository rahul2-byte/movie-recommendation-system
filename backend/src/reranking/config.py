from typing import List

# -------------------------------
# Re-ranking parameters
# -------------------------------

TOP_K_FINAL = 20          # final items returned to user
CANDIDATE_POOL = 200      # ranked candidates input to reranker

# Diversity
MAX_ITEMS_PER_GENRE = 3
MAX_ITEMS_PER_FRANCHISE = 2

# Freshness
FRESHNESS_HALF_LIFE_DAYS = 30
FRESHNESS_WEIGHT = 0.2   # how much freshness can influence score

# Fields expected in item metadata
GENRE_FIELD = "genres"
FRANCHISE_FIELD = "franchise"
RELEASE_TS_FIELD = "release_timestamp"
