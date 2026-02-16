import pandas as pd
import numpy as np
import logging
import time
from typing import List, Dict, Any
from collections import Counter

log = logging.getLogger(__name__)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


class FeatureBuilder:
    def __init__(self):
        # Stateless!
        pass

    def build_features(
        self, 
        query_seeds: List[Dict[str, Any]], 
        candidates: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Build features dynamically from Seed Metadata and Candidate Metadata.
        """
        start_time = time.time()
        
        # 1. Analyze Query (Seeds)
        # ------------------------
        if not query_seeds:
            log.warning("No query seeds provided for feature building.")
            return pd.DataFrame()
            
        # Stats
        seed_years = [
            _to_int(s.get('year') if s.get('year') is not None else s.get('release_year'))
            for s in query_seeds
        ]
        seed_ratings = [
            _to_float(s.get('rating') if s.get('rating') is not None else s.get('vote_average'))
            for s in query_seeds
        ]
        seed_runtimes = [_to_float(s.get('runtime_minutes')) for s in query_seeds]
        
        avg_year = np.mean([y for y in seed_years if y > 0]) if any(y > 0 for y in seed_years) else 0
        avg_rating = np.mean(seed_ratings)
        avg_runtime = np.mean([r for r in seed_runtimes if r > 0]) if any(r > 0 for r in seed_runtimes) else 0
        
        # Vector Counters (Genre & Tag)
        # We count how many seeds have 'Action', 'Sci-Fi', etc.
        # This acts as the "Query Vector" (e.g. Action: 2, Sci-Fi: 1)
        genre_counter = Counter()
        tag_counter = Counter()
        
        for s in query_seeds:
            # Genres
            genres = s.get('genres', [])
            if isinstance(genres, str): genres = genres.split('|')
            for g in genres:
                if g: genre_counter[str(g).lower()] += 1
                
            # Tags (User Tags or Keywords)
            tags = s.get('user_tags', []) + s.get('keywords', [])
            if isinstance(tags, str): tags = [tags] # Should be list
            for t in tags:
                if t: tag_counter[str(t).lower()] += 1
                
        # 2. Score Candidates
        # -------------------
        features = []
        
        for cand in candidates:
            # Metadata
            c_id = cand.get('movieId')
            c_year = _to_int(cand.get('year') if cand.get('year') is not None else cand.get('release_year'))
            c_rating = _to_float(cand.get('rating') if cand.get('rating') is not None else cand.get('vote_average'))
            c_votes = _to_int(cand.get('vote_count'))
            c_pop = _to_float(cand.get('popularity') if cand.get('popularity') is not None else cand.get('popularity_score'))
            c_runtime = _to_float(cand.get('runtime_minutes'))
            c_imdb_rating = _to_float(cand.get('imdb_rating'))
            c_imdb_votes = _to_int(cand.get('imdb_votes'))
            
            # Genres
            c_genres = cand.get('genres', [])
            if isinstance(c_genres, str): c_genres = c_genres.split('|')
            c_genres_lower = [str(g).lower() for g in c_genres if g]
            
            # Tags
            c_tags = cand.get('user_tags', []) + cand.get('keywords', [])
            c_tags_lower = [str(t).lower() for t in c_tags if t]
            
            # Compute Overlaps (Dot Product equivalent)
            # sum(query_weight * 1 if candidate_has else 0)
            genre_overlap = sum(genre_counter[g] for g in c_genres_lower)
            tag_overlap = sum(tag_counter[t] for t in c_tags_lower)
            
            # Diffs
            year_diff = abs(c_year - avg_year) if (c_year > 0 and avg_year > 0) else 0
            runtime_diff = abs(c_runtime - avg_runtime) if (c_runtime > 0 and avg_runtime > 0) else 0
            
            features.append({
                "candidate_movie_id": c_id,
                # Query Features
                "feat_avg_query_rating": avg_rating,
                "feat_avg_query_year": avg_year,
                "feat_avg_query_runtime": avg_runtime,
                # Candidate Features
                "feat_candidate_avg_rating": c_rating,
                "feat_candidate_rating_count": c_votes,
                "feat_candidate_popularity": c_pop,
                "feat_candidate_imdb_rating": c_imdb_rating,
                "feat_candidate_imdb_votes": c_imdb_votes,
                "feat_candidate_year": c_year,
                "feat_candidate_runtime": c_runtime,
                # Interaction Features
                "feat_genre_overlap": genre_overlap,
                "feat_tag_overlap": tag_overlap,
                "feat_year_diff": year_diff,
                "feat_runtime_diff": runtime_diff,
            })
            
        df = pd.DataFrame(features)
        
        # Ensure ID column is present even if empty
        if df.empty:
            return pd.DataFrame(columns=["candidate_movie_id"])
            
        log.info(f"Built features for {len(candidates)} candidates in {time.time() - start_time:.4f}s")
        return df

    @classmethod
    def from_dataframe(cls, *args, **kwargs):
        # Backwards compatibility dummy
        return cls()
