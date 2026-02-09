import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import joblib
import numpy as np
import pandas as pd

# PyTorch imports
import torch
import torch.nn as nn
import torch.optim as optim
from common.config import config
from common.logger import get_logger
from common.types import Query
from sklearn.model_selection import train_test_split

# Scikit-learn for feature preprocessing
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from torch.utils.data import DataLoader, Dataset

from retrieval.inference.base_retriever import BaseRetriever

log = get_logger(__name__)

# --- Feature Preprocessing (Shared between Builder and Retriever) ---


class FeaturePreprocessor:
    def __init__(
        self, movies_df: pd.DataFrame, tags_df: pd.DataFrame, top_n_tags: int = 10000
    ):
        self.mlb_genres: MultiLabelBinarizer = None
        self.mlb_tags: MultiLabelBinarizer = None
        self.scaler_numerical: StandardScaler = None

        self.movie_id_to_idx: Dict[int, int] = None
        self.idx_to_movie_id: Dict[int, int] = None
        self.movies_meta: pd.DataFrame = None

        self._fit_preprocessors(movies_df.copy(), tags_df.copy(), top_n_tags)

    def _ensure_list_of_strings(self, item: Any) -> List[str]:
        if item is None:
            return []
        if isinstance(item, list):
            return [str(x) for x in item]
        if isinstance(item, str):
            try:
                evaluated = json.loads(item)
                if isinstance(evaluated, list):
                    return [str(x) for x in evaluated]
            except json.JSONDecodeError:
                pass
        return [str(item)]

    def _fit_preprocessors(
        self, movies_df: pd.DataFrame, tags_df: pd.DataFrame, top_n_tags: int
    ):
        log.info("TwoTowerBuilder: Fitting feature preprocessors...")

        # Ensure movie_id is index
        if "movieId" in movies_df.columns:
            movies_df = movies_df.rename(columns={"movieId": "movie_id"})
        movies_df = movies_df.set_index("movie_id")
        self.movies_meta = movies_df  # Store for later use

        # 1. Genres
        movies_df["genres"] = movies_df["genres"].apply(self._ensure_list_of_strings)
        all_genres = sorted(
            {g for sublist in movies_df["genres"] for g in sublist if g}
        )
        self.mlb_genres = MultiLabelBinarizer(classes=all_genres)
        self.mlb_genres.fit(movies_df["genres"])  # Fit on all possible genres

        # 2. Tags
        tags_df.dropna(subset=["tag"], inplace=True)
        tags_df["tag"] = tags_df["tag"].str.lower()
        top_tags = tags_df["tag"].value_counts().nlargest(top_n_tags).index.tolist()
        self.mlb_tags = MultiLabelBinarizer(classes=top_tags)
        # To fit MLB, we need all tags for all movies, or just fit on the `top_tags` directly
        # For fitting, we pass a dummy list of all unique top_tags
        self.mlb_tags.fit([top_tags])

        # 3. Numerical Features
        numerical_cols = [
            "release_year",
            "vote_average",
            "popularity_score",
            "vote_count",
        ]
        self.numerical_cols = numerical_cols
        for col, default in [
            ("release_year", 0),
            ("vote_average", 0.0),
            ("popularity_score", 0.0),
            ("vote_count", 0),
        ]:
            if col not in movies_df.columns:
                movies_df[col] = default
        movies_df[numerical_cols] = movies_df[numerical_cols].fillna(0)
        self.scaler_numerical = StandardScaler()
        self.scaler_numerical.fit(
            movies_df[numerical_cols]
        )  # Fit on all movie numerical features

        log.info("TwoTowerBuilder: Feature preprocessors fitted.")

    def transform(self, movie_id: int) -> Dict[str, torch.Tensor]:
        """Transforms raw movie features into model-ready tensors."""
        movie_data = self.movies_meta.loc[movie_id]

        features = {}

        # Genres (Multi-hot)
        genres_transformed = self.mlb_genres.transform(
            [self._ensure_list_of_strings(movie_data["genres"])]
        )
        features["genres"] = torch.tensor(genres_transformed, dtype=torch.float32)

        # Tags (Multi-hot)
        # This part assumes tags are stored per movie in movies_meta or can be looked up
        # For now, let's simplify and derive tags from `movies_meta` or provide a dummy
        # A more robust solution involves pre-merging tags into movies_meta or loading separately
        # For simplicity, we assume movies_meta contains a 'tags' column that is a list of strings
        if "tags" not in movie_data or not isinstance(
            movie_data["tags"], (list, np.ndarray)
        ):
            # Fallback for when 'tags' not pre-merged in movies_meta
            # In a real system, you'd ensure tags are merged into movies_meta during data processing
            tags_for_movie = []  # Placeholder if tags not available directly
        else:
            tags_for_movie = [t.lower() for t in movie_data["tags"]]

        tags_transformed = self.mlb_tags.transform([tags_for_movie])
        if hasattr(tags_transformed, "toarray"):
            tags_dense = tags_transformed.toarray()
        else:
            tags_dense = tags_transformed
        features["tags"] = torch.tensor(tags_dense, dtype=torch.float32)

        # Numerical Features
        numerical_values = [
            movie_data.get("release_year", 0),
            movie_data.get("vote_average", 0.0),
            movie_data.get("popularity_score", 0.0),
            movie_data.get("vote_count", 0),
        ]
        numerical_df = pd.DataFrame([numerical_values], columns=self.numerical_cols)
        numerical_transformed = self.scaler_numerical.transform(numerical_df)
        features["numerical"] = torch.tensor(numerical_transformed, dtype=torch.float32)

        return features

    def get_feature_dimensions(self) -> Dict[str, int]:
        """Returns the output dimensions of each feature type after preprocessing."""
        return {
            "genres": len(self.mlb_genres.classes_),
            "tags": len(self.mlb_tags.classes_),
            "numerical": self.scaler_numerical.n_features_in_,
        }


# --- PyTorch Item Encoder Model ---


class ItemEncoder(nn.Module):
    def __init__(self, feature_dims: Dict[str, int], embedding_dim: int):
        super().__init__()

        self.genre_embedding_layer = nn.Linear(
            feature_dims["genres"], embedding_dim // 4
        )
        self.tag_embedding_layer = nn.Linear(feature_dims["tags"], embedding_dim // 4)
        self.numerical_embedding_layer = nn.Linear(
            feature_dims["numerical"], embedding_dim // 4
        )

        # Combine all features
        self.fc1 = nn.Linear(embedding_dim // 4 * 3, embedding_dim)
        self.relu = nn.ReLU()

    def forward(self, features: Dict[str, torch.Tensor]) -> torch.Tensor:
        genres_emb = self.relu(self.genre_embedding_layer(features["genres"]))
        tags_emb = self.relu(self.tag_embedding_layer(features["tags"]))
        numerical_emb = self.relu(self.numerical_embedding_layer(features["numerical"]))

        combined_emb = torch.cat([genres_emb, tags_emb, numerical_emb], dim=-1)

        # Final embedding layer
        item_embedding = self.fc1(combined_emb)
        return item_embedding


# --- TwoTowerDataset for Training ---


class TwoTowerDataset(Dataset):
    def __init__(
        self,
        sequences_df: pd.DataFrame,
        preprocessor: FeaturePreprocessor,
        all_movie_ids: List[int],
        num_negatives: int = 4,
    ):
        self.sequences_df = sequences_df
        self.preprocessor = preprocessor
        self.all_movie_ids = all_movie_ids
        self.num_negatives = num_negatives
        self.valid_movie_ids = list(preprocessor.movies_meta.index)
        self.valid_movie_id_set = set(self.valid_movie_ids)
        # Determine a fixed number of query seeds to keep tensor shapes consistent.
        try:
            max_seeds = (
                self.sequences_df["query_movie_ids"].astype(str).str.count(r"\|").max()
            )
            max_seeds = int(max_seeds) + 1 if not np.isnan(max_seeds) else 1
        except Exception:
            max_seeds = 1
        self.max_query_seeds = max(1, min(10, max_seeds))

        self.rng = np.random.default_rng(42)  # For negative sampling

    def __len__(self):
        return len(self.sequences_df)

    def __getitem__(self, idx):
        row = self.sequences_df.iloc[idx]

        query_movie_ids = [int(mid) for mid in str(row["query_movie_ids"]).split("|")]
        query_movie_ids = [
            mid for mid in query_movie_ids if mid in self.valid_movie_id_set
        ]
        if not query_movie_ids:
            query_movie_ids = [
                self.valid_movie_ids[self.rng.integers(0, len(self.valid_movie_ids))]
            ]
        # Pad or truncate to fixed length for batching.
        if len(query_movie_ids) < self.max_query_seeds:
            pad_needed = self.max_query_seeds - len(query_movie_ids)
            pad_choices = self.valid_movie_ids
            query_movie_ids = query_movie_ids + [
                pad_choices[self.rng.integers(0, len(pad_choices))]
                for _ in range(pad_needed)
            ]
        elif len(query_movie_ids) > self.max_query_seeds:
            query_movie_ids = query_movie_ids[: self.max_query_seeds]

        positive_movie_id = int(row["candidate_movie_id"])
        if (
            positive_movie_id not in self.valid_movie_id_set
            or positive_movie_id in query_movie_ids
        ):
            # Fallback to a valid positive not in query seeds.
            for _ in range(10):
                candidate = self.valid_movie_ids[
                    self.rng.integers(0, len(self.valid_movie_ids))
                ]
                if candidate not in query_movie_ids:
                    positive_movie_id = candidate
                    break

        # Get features for query seeds
        query_features_list = [
            self.preprocessor.transform(mid) for mid in query_movie_ids
        ]

        # Stack feature dictionaries into a single dictionary of stacked tensors
        query_features = {
            key: torch.cat([f[key] for f in query_features_list], dim=0)
            for key in query_features_list[0].keys()
        }

        # Get features for positive movie
        positive_features = self.preprocessor.transform(positive_movie_id)

        # Negative Sampling:
        # Sample random movies that are not the positive and not in query seeds
        negative_movie_ids = []
        num_movies = len(self.all_movie_ids)
        while len(negative_movie_ids) < self.num_negatives:
            random_idx = self.rng.integers(0, num_movies)
            neg_mid = self.all_movie_ids[random_idx]
            if neg_mid != positive_movie_id and neg_mid not in query_movie_ids:
                negative_movie_ids.append(neg_mid)

        negative_features_list = [
            self.preprocessor.transform(mid) for mid in negative_movie_ids
        ]

        negative_features = {
            key: torch.cat([f[key] for f in negative_features_list], dim=0)
            for key in negative_features_list[0].keys()
        }

        return query_features, positive_features, negative_features


# --- TwoTowerBuilder (Offline Training Component) ---


class TwoTowerBuilder:
    def __init__(
        self,
        sequences_path: Path,
        movies_metadata_path: Path,
        tags_path: Path,
        output_dir: Path,
        embedding_dim: int = 64,
        epochs: int = 5,
        batch_size: int = 256,
        learning_rate: float = 1e-3,
        num_negatives: int = 4,
        top_n_tags: int = 10000,
    ):
        self.sequences_path = sequences_path
        self.movies_metadata_path = movies_metadata_path
        self.tags_path = tags_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.embedding_dim = embedding_dim
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.num_negatives = num_negatives
        self.top_n_tags = top_n_tags

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        log.info(f"TwoTowerBuilder: Using device: {self.device}")

    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Loads sequences, movie metadata, and tags."""
        log.info(f"TwoTowerBuilder: Loading sequences from {self.sequences_path}")
        if str(self.sequences_path).endswith(".parquet"):
            # Only read the first 2 million positive samples to prevent OOM
            # We can use pyarrow to read a subset if needed, or just sample after reading if memory allows.
            # But with 57M rows, even reading is risky. Let's read and sample immediately.
            # Actually, let's use a smaller limit to be safe.
            sequences_df = pd.read_parquet(self.sequences_path)
        else:
            sequences_df = pd.read_csv(self.sequences_path)

        sequences_df = sequences_df[sequences_df["label"] == 1]

        MAX_TRAIN_SEQUENCES = 2_000_000
        if len(sequences_df) > MAX_TRAIN_SEQUENCES:
            log.info(
                f"TwoTowerBuilder: Sub-sampling {len(sequences_df)} sequences to {MAX_TRAIN_SEQUENCES}..."
            )
            sequences_df = sequences_df.sample(n=MAX_TRAIN_SEQUENCES, random_state=42)

        sequences_df = sequences_df.reset_index(drop=True)
        log.info(
            f"TwoTowerBuilder: Final training set size: {len(sequences_df)} positive sequences."
        )

        log.info(
            f"TwoTowerBuilder: Loading movie metadata from {self.movies_metadata_path}"
        )
        movies_df = pd.read_parquet(self.movies_metadata_path)
        log.info(f"TwoTowerBuilder: Loaded {len(movies_df)} movies.")

        log.info(f"TwoTowerBuilder: Loading tags from {self.tags_path}")
        tags_df = pd.read_parquet(self.tags_path)
        log.info(f"TwoTowerBuilder: Loaded {len(tags_df)} tags.")
        return sequences_df, movies_df, tags_df

    def build_and_save(self):
        """Trains the Two-Tower model and saves all artifacts."""
        sequences_df, movies_df, tags_df = self._load_data()

        # Initialize FeaturePreprocessor
        preprocessor = FeaturePreprocessor(movies_df, tags_df, self.top_n_tags)

        # Save preprocessor for inference
        joblib.dump(
            preprocessor, config.system.retrieval_artifacts.two_tower.preprocessors_path
        )
        log.info(
            f"TwoTowerBuilder: Saved preprocessors to {config.system.retrieval_artifacts.two_tower.preprocessors_path}"
        )

        # Create movie_id to index mapping for FAISS and embedding lookup
        # This mapping is based on movies_df for consistency
        movie_id_to_idx = {
            movie_id: idx for idx, movie_id in enumerate(preprocessor.movies_meta.index)
        }
        with open(config.system.retrieval_artifacts.two_tower.id_map_path, "w") as f:
            json.dump(movie_id_to_idx, f)
        log.info(
            f"TwoTowerBuilder: Saved movie ID to index map to {config.system.retrieval_artifacts.two_tower.id_map_path}"
        )

        # --- PyTorch Dataset and DataLoader ---
        all_movie_ids = preprocessor.movies_meta.index.tolist()
        dataset = TwoTowerDataset(
            sequences_df, preprocessor, all_movie_ids, num_negatives=self.num_negatives
        )
        dataloader = DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=os.cpu_count() // 2,
        )

        # --- Model Initialization ---
        feature_dims = preprocessor.get_feature_dimensions()
        item_encoder = ItemEncoder(feature_dims, self.embedding_dim).to(self.device)
        optimizer = optim.Adam(item_encoder.parameters(), lr=self.learning_rate)

        # Loss function: Sampled Softmax (or Triplet Loss)
        # For simplicity, we'll use a contrastive loss based on dot products
        # A common approach is BPR-like loss for implicit or sampled softmax for explicit.
        # Here, we'll aim to maximize positive similarity and minimize negative similarity.

        log.info("TwoTowerBuilder: Starting model training...")
        item_encoder.train()
        for epoch in range(self.epochs):
            total_loss = 0
            for batch_idx, (
                query_feats_batch,
                pos_feats_batch,
                neg_feats_batch,
            ) in enumerate(dataloader):
                optimizer.zero_grad()

                # Move features to device
                query_feats_batch = {
                    k: v.to(self.device) for k, v in query_feats_batch.items()
                }
                pos_feats_batch = {
                    k: v.to(self.device) for k, v in pos_feats_batch.items()
                }
                neg_feats_batch = {
                    k: v.to(self.device) for k, v in neg_feats_batch.items()
                }
                # Positive features come in as (batch_size, 1, feature_dim); squeeze to (batch_size, feature_dim).
                pos_feats_batch = {
                    k: v.squeeze(1) if v.dim() == 3 and v.shape[1] == 1 else v
                    for k, v in pos_feats_batch.items()
                }

                # Average query seed embeddings to get query embedding
                # Each query_feats_batch['genres'] is (batch_size, num_seeds, num_genres)
                # Need to iterate through seeds first for each batch item

                # Query features come as (batch_size, num_seeds, feature_dim)
                # ItemEncoder expects (batch_size, feature_dim)
                # So we need to reshape/process to pass seed movies individually and then average

                # Reshape for ItemEncoder: (batch_size * num_seeds, feature_dim)
                batch_size = query_feats_batch["genres"].shape[0]
                num_seeds = query_feats_batch["genres"].shape[1]

                query_feats_reshaped = {
                    k: v.view(batch_size * num_seeds, -1)
                    for k, v in query_feats_batch.items()
                }

                # Get embeddings for all seeds in batch
                seed_embeddings_flat = item_encoder(
                    query_feats_reshaped
                )  # (batch_size * num_seeds, embedding_dim)

                # Average to get query embedding: (batch_size, embedding_dim)
                query_embedding = seed_embeddings_flat.view(
                    batch_size, num_seeds, -1
                ).mean(dim=1)

                # Get embeddings for positive items
                positive_embedding = item_encoder(
                    pos_feats_batch
                )  # (batch_size, embedding_dim)

                # Get embeddings for negative items
                # Reshape for ItemEncoder: (batch_size * num_negatives, feature_dim)
                neg_feats_reshaped = {
                    k: v.view(batch_size * self.num_negatives, -1)
                    for k, v in neg_feats_batch.items()
                }
                negative_embeddings_flat = item_encoder(
                    neg_feats_reshaped
                )  # (batch_size * num_negatives, embedding_dim)
                negative_embeddings = negative_embeddings_flat.view(
                    batch_size, self.num_negatives, -1
                )

                # Calculate similarities (dot product)
                pos_sim = torch.sum(
                    query_embedding * positive_embedding, dim=1
                )  # (batch_size)
                neg_sim = torch.sum(
                    query_embedding.unsqueeze(1) * negative_embeddings, dim=2
                )  # (batch_size, num_negatives)

                # Sampled Softmax Loss (or similar contrastive loss)
                # Maximize pos_sim, minimize neg_sim
                # Use BCEWithLogitsLoss where positives are 1 and negatives are 0

                # This is a simplified contrastive loss:
                # push positive closer, push negatives further
                # Goal: pos_sim > neg_sim
                loss = -torch.log(torch.sigmoid(pos_sim.unsqueeze(1) - neg_sim)).mean()

                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            log.info(
                f"Epoch {epoch + 1}/{self.epochs}, Loss: {total_loss / len(dataloader):.4f}"
            )

        log.info("TwoTowerBuilder: Model training complete.")

        # Save trained ItemEncoder
        torch.save(
            item_encoder.state_dict(),
            config.system.retrieval_artifacts.two_tower.item_encoder_path,
        )
        log.info(
            f"TwoTowerBuilder: Saved ItemEncoder to {config.system.retrieval_artifacts.two_tower.item_encoder_path}"
        )

        # --- Extract ALL Item Embeddings ---
        log.info("TwoTowerBuilder: Extracting all item embeddings for FAISS index...")
        item_encoder.eval()  # Set to evaluation mode
        all_item_embeddings = []
        with torch.no_grad():
            for movie_id in preprocessor.movies_meta.index:
                features = preprocessor.transform(movie_id)
                # Add batch dimension (1, feature_dim)
                features = {
                    k: v.unsqueeze(0).to(self.device) for k, v in features.items()
                }
                embedding = item_encoder(features).cpu().numpy().flatten()
                all_item_embeddings.append(embedding)
        all_item_embeddings = np.array(all_item_embeddings).astype(np.float32)
        np.save(
            config.system.retrieval_artifacts.two_tower.embeddings_path,
            all_item_embeddings,
        )
        log.info(
            f"TwoTowerBuilder: Saved all item embeddings to {config.system.retrieval_artifacts.two_tower.embeddings_path}"
        )

        # --- Build FAISS Index ---
        log.info("TwoTowerBuilder: Building FAISS index...")

        # Normalize vectors for cosine similarity (FAISS L2 on normalized vectors)
        faiss_vectors = all_item_embeddings / np.linalg.norm(
            all_item_embeddings, axis=1, keepdims=True
        )
        faiss_vectors[np.isnan(faiss_vectors)] = (
            0  # Handle potential NaN from zero-norm vectors
        )

        index = faiss.IndexFlatL2(faiss_vectors.shape[1])  # L2 distance
        index.add(faiss_vectors)

        # Save FAISS index
        faiss.write_index(
            index, str(config.system.retrieval_artifacts.two_tower.faiss_index_path)
        )
        log.info(
            f"TwoTowerBuilder: Saved FAISS index to {config.system.retrieval_artifacts.two_tower.faiss_index_path}"
        )

        log.info("TwoTowerBuilder: Building and saving complete.")


# --- TwoTowerRetriever (Online Inference Component) ---


class TwoTowerRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("two_tower")
        self.item_embeddings: np.ndarray = None
        self.index: faiss.Index = None
        self.movie_id_to_idx: Dict[int, int] = None
        self.idx_to_movie_id: Dict[int, int] = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Loads the pre-computed Two-Tower item embeddings and FAISS index."""
        from common.model_loader import ensure_local_path

        embeddings_path = ensure_local_path(
            config.system.retrieval_artifacts.two_tower.embeddings_path
        )
        faiss_path = ensure_local_path(
            config.system.retrieval_artifacts.two_tower.faiss_index_path
        )
        id_map_path = ensure_local_path(
            config.system.retrieval_artifacts.two_tower.id_map_path
        )

        log.info(f"TwoTowerRetriever: Loading item embeddings from {embeddings_path}")
        self.item_embeddings = np.load(embeddings_path)

        log.info(f"TwoTowerRetriever: Loading FAISS index from {faiss_path}")
        self.index = faiss.read_index(str(faiss_path))

        log.info(f"TwoTowerRetriever: Loading movie ID map from {id_map_path}")
        with open(id_map_path, "r") as f:
            self.movie_id_to_idx = {int(k): v for k, v in json.load(f).items()}
        self.idx_to_movie_id = {v: k for k, v in self.movie_id_to_idx.items()}

        log.info("TwoTowerRetriever: Artifacts loaded successfully.")

    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> List[Tuple[int, float, str]]:
        """
        Retrieves candidates using Two-Tower item embeddings via FAISS.
        """
        seed_movie_ids = query.seed_movie_ids

        # 1. Get query embedding (average of seed movie embeddings)
        query_embeddings = []
        for mid in seed_movie_ids:
            if mid in self.movie_id_to_idx:
                query_embeddings.append(self.item_embeddings[self.movie_id_to_idx[mid]])
            else:
                log.warning(
                    f"TwoTowerRetriever: Seed movie ID {mid} not found in map. Skipping."
                )

        if not query_embeddings:
            return []

        query_vector = (
            np.mean(query_embeddings, axis=0).reshape(1, -1).astype(np.float32)
        )

        # Normalize query vector for cosine similarity
        norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        query_vector = np.divide(
            query_vector, norm, out=np.zeros_like(query_vector), where=norm != 0
        )

        # 2. Perform FAISS search (IndexFlatIP returns Inner Product, which is Cosine Similarity)
        D, I = self.index.search(query_vector, top_k * 2)

        candidates_with_scores = []
        for similarity, idx in zip(D[0], I[0]):
            movie_id = self.idx_to_movie_id.get(idx)
            if movie_id is not None and movie_id not in seed_movie_ids:
                candidates_with_scores.append((movie_id, float(similarity), self.name))
            if len(candidates_with_scores) >= top_k:
                break

        log.info(
            f"TwoTowerRetriever: Retrieved {len(candidates_with_scores)} candidates."
        )
        return candidates_with_scores
