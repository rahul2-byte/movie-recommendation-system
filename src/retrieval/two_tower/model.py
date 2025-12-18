# src/retrieval/two_tower/model.py
"""
Two-Tower model definition for retrieval.

Design goals:
- Small, efficient embedding towers (embedding + small MLP).
- Embeddings are L2-normalized for cosine/inner-product retrieval.
- Modular: easy to extend with side-features later.
"""

from typing import List, Optional
import math

import torch
import torch.nn as nn


class MLP(nn.Module):
    """Lightweight MLP with ReLU and dropout. Keeps parameter count low."""

    def __init__(self, input_dim: int, hidden_dims: Optional[List[int]] = None, dropout: float = 0.0):
        super().__init__()
        hidden_dims = hidden_dims or []
        layers: List[nn.Module] = []
        in_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.ReLU(inplace=True))
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_dim = h
        # final projection to same dim if last hidden != input_dim is not necessary here
        self.net = nn.Sequential(*layers) if layers else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Tower(nn.Module):
    """
    Single tower: embedding for ID followed by optional MLP.

    Args:
        num_ids: size of vocabulary (users or items).
        emb_dim: embedding dimension.
        mlp_hidden_dims: optional hidden dims for MLP.
        dropout: dropout rate.
        embedding_init_std: std for embedding initialization (smaller is stable).
    """

    def __init__(
        self,
        num_ids: int,
        emb_dim: int,
        mlp_hidden_dims: Optional[List[int]] = None,
        dropout: float = 0.0,
        embedding_init_std: float = 0.01,
    ):
        super().__init__()
        self.id_emb = nn.Embedding(num_ids, emb_dim)
        # initialize embedding with small std for numeric stability
        nn.init.normal_(self.id_emb.weight, mean=0.0, std=embedding_init_std)
        self.mlp = MLP(emb_dim, mlp_hidden_dims, dropout)
        # optionally a projection to emb_dim (identity if mlp ends in emb_dim)
        if mlp_hidden_dims and mlp_hidden_dims[-1] != emb_dim:
            self.project = nn.Linear(mlp_hidden_dims[-1], emb_dim)
        else:
            self.project = nn.Identity()
        # layer norm helps training stability
        self.norm = nn.LayerNorm(emb_dim)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """
        Args:
            ids: LongTensor of shape (B,) or (B, seq?) — typically (B,)
        Returns:
            embeddings: Tensor (B, emb_dim)
        """
        x = self.id_emb(ids)
        x = self.mlp(x)
        x = self.project(x)
        x = self.norm(x)
        return x


class TwoTower(nn.Module):
    """
    Two-Tower retrieval model.

    Usage:
        user_emb, item_emb = model(user_ids, item_ids)
    """

    def __init__(
        self,
        num_users: int,
        num_items: int,
        emb_dim: int = 128,
        user_mlp: Optional[List[int]] = None,
        item_mlp: Optional[List[int]] = None,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.user_tower = Tower(num_users, emb_dim, user_mlp, dropout)
        self.item_tower = Tower(num_items, emb_dim, item_mlp, dropout)

    def forward(self, user_ids: torch.Tensor, item_ids: torch.Tensor) -> (torch.Tensor, torch.Tensor):
        """
        Compute user and item embeddings and normalize them.

        Returns normalized embeddings (L2 norm 1) for stable dot-product/cosine behaviour.
        """
        u = self.user_tower(user_ids)
        v = self.item_tower(item_ids)
        # normalize to L2=1 to make dot-product ~ cosine similarity
        u = nn.functional.normalize(u, p=2, dim=-1)
        v = nn.functional.normalize(v, p=2, dim=-1)
        return u, v

    def encode_users(self, user_ids: torch.Tensor) -> torch.Tensor:
        """Return normalized user embeddings"""
        with torch.no_grad():
            u = self.user_tower(user_ids)
            u = nn.functional.normalize(u, p=2, dim=-1)
            return u

    def encode_items(self, item_ids: torch.Tensor) -> torch.Tensor:
        """Return normalized item embeddings"""
        with torch.no_grad():
            v = self.item_tower(item_ids)
            v = nn.functional.normalize(v, p=2, dim=-1)
            return v
