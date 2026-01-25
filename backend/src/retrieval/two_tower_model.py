"""
Two-Tower Retrieval Model (Single File)

Features:
- In-batch negatives (InfoNCE)
- Mixed precision (bf16 / fp16)
- Gradient accumulation
- torch.compile support
- Cosine LR with warmup
- Smart checkpointing
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)


# ============================================================
# Utilities
# ============================================================

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ============================================================
# Model Components
# ============================================================

class MLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Optional[List[int]] = None,
        dropout: float = 0.0,
    ):
        super().__init__()
        hidden_dims = hidden_dims or []
        layers: List[nn.Module] = []

        in_dim = input_dim
        for h in hidden_dims:
            layers += [
                nn.Linear(in_dim, h),
                nn.ReLU(inplace=True),
            ]
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_dim = h

        self.net = nn.Sequential(*layers) if layers else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Tower(nn.Module):
    def __init__(
        self,
        num_ids: int,
        emb_dim: int,
        mlp_hidden_dims: Optional[List[int]],
        dropout: float,
        init_std: float = 0.01,
    ):
        super().__init__()
        self.embedding = nn.Embedding(num_ids, emb_dim)
        nn.init.normal_(self.embedding.weight, mean=0.0, std=init_std)

        self.mlp = MLP(emb_dim, mlp_hidden_dims, dropout)
        self.project = (
            nn.Linear(mlp_hidden_dims[-1], emb_dim)
            if mlp_hidden_dims and mlp_hidden_dims[-1] != emb_dim
            else nn.Identity()
        )
        self.norm = nn.LayerNorm(emb_dim)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        x = self.embedding(ids)
        x = self.mlp(x)
        x = self.project(x)
        return self.norm(x)


class TwoTower(nn.Module):
    def __init__(
        self,
        num_users: int,
        num_items: int,
        emb_dim: int,
        user_mlp: Optional[List[int]],
        item_mlp: Optional[List[int]],
        dropout: float,
    ):
        super().__init__()
        self.user_tower = Tower(num_users, emb_dim, user_mlp, dropout)
        self.item_tower = Tower(num_items, emb_dim, item_mlp, dropout)

    def forward(
        self,
        user_ids: torch.Tensor,
        item_ids: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        u = F.normalize(self.user_tower(user_ids), dim=-1)
        v = F.normalize(self.item_tower(item_ids), dim=-1)
        return u, v

    @torch.no_grad()
    def encode_users(self, user_ids: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.user_tower(user_ids), dim=-1)

    @torch.no_grad()
    def encode_items(self, item_ids: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.item_tower(item_ids), dim=-1)


# ============================================================
# Dataset
# ============================================================

class InteractionDataset(Dataset):
    def __init__(self, df: pd.DataFrame):
        self.users = torch.from_numpy(df["userId"].values.astype(np.int64))
        self.items = torch.from_numpy(df["movieId"].values.astype(np.int64))

    def __len__(self) -> int:
        return len(self.users)

    def __getitem__(self, idx: int):
        return self.users[idx], self.items[idx]


# ============================================================
# Loss
# ============================================================

@torch.jit.script
def info_nce_loss(
    user_emb: torch.Tensor,
    item_emb: torch.Tensor,
    temperature: float,
) -> torch.Tensor:
    logits = (user_emb @ item_emb.T) / temperature
    labels = torch.arange(logits.size(0), device=logits.device)
    return 0.5 * (
        F.cross_entropy(logits, labels)
        + F.cross_entropy(logits.T, labels)
    )


# ============================================================
# Scheduler
# ============================================================

class CosineWarmupScheduler:
    def __init__(
        self,
        optimizer: torch.optim.Optimizer,
        warmup_steps: int,
        total_steps: int,
        min_lr_ratio: float = 0.1,
    ):
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.min_lr_ratio = min_lr_ratio
        self.base_lrs = [g["lr"] for g in optimizer.param_groups]

    def step(self, step: int):
        if step < self.warmup_steps:
            mult = step / max(1, self.warmup_steps)
        else:
            p = (step - self.warmup_steps) / max(
                1, self.total_steps - self.warmup_steps
            )
            mult = self.min_lr_ratio + (1 - self.min_lr_ratio) * 0.5 * (
                1 + np.cos(np.pi * p)
            )

        for g, base_lr in zip(self.optimizer.param_groups, self.base_lrs):
            g["lr"] = base_lr * mult


# ============================================================
# Training
# ============================================================

def train_two_tower(
    train_path: str,
    out_dir: str,
    emb_dim: int,
    user_mlp: Optional[List[int]],
    item_mlp: Optional[List[int]],
    dropout: float,
    batch_size: int,
    epochs: int,
    lr: float,
    weight_decay: float,
    temperature: float,
    seed: int,
    amp: bool,
    grad_accum_steps: int,
    compile_model: bool,
    num_workers: int,
    resume_from: Optional[str],
) -> None:

    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    df = pd.read_csv(train_path)

    user_codes = pd.Categorical(df["userId"])
    item_codes = pd.Categorical(df["movieId"])

    df["userId"] = user_codes.codes.astype(np.int64)
    df["movieId"] = item_codes.codes.astype(np.int64)

    num_users = len(user_codes.categories)
    num_items = len(item_codes.categories)

    # Save metadata + ID maps
    with open(out_dir / "id_maps.json", "w") as f:
        json.dump(
            {
                "user_id_map": dict(enumerate(user_codes.categories.tolist())),
                "item_id_map": dict(enumerate(item_codes.categories.tolist())),
            },
            f,
        )

    with open(out_dir / "meta.json", "w") as f:
        json.dump(
            {
                "num_users": num_users,
                "num_items": num_items,
                "emb_dim": emb_dim,
                "user_mlp": user_mlp,
                "item_mlp": item_mlp,
                "dropout": dropout,
            },
            f,
            indent=2,
        )

    dataset = InteractionDataset(df)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers if use_cuda else 0,
        pin_memory=use_cuda,
        drop_last=True,
    )

    model = TwoTower(
        num_users,
        num_items,
        emb_dim,
        user_mlp,
        item_mlp,
        dropout,
    ).to(device)

    if compile_model and hasattr(torch, "compile") and use_cuda:
        model = torch.compile(model)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay,
        fused=use_cuda,
    )

    total_steps = len(loader) * epochs // grad_accum_steps
    scheduler = CosineWarmupScheduler(
        optimizer,
        warmup_steps=min(500, total_steps // 10),
        total_steps=total_steps,
    )

    scaler = torch.amp.GradScaler(
        device.type,
        enabled=(amp and use_cuda),
    )

    best_loss = float("inf")
    global_step = 0

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0

        optimizer.zero_grad(set_to_none=True)

        for step, (u, i) in enumerate(loader, start=1):
            u = u.to(device, non_blocking=True)
            i = i.to(device, non_blocking=True)

            with torch.amp.autocast(
                device_type=device.type,
                enabled=(amp and use_cuda),
            ):
                ue, ie = model(u, i)
                loss = info_nce_loss(ue, ie, temperature)
                loss = loss / grad_accum_steps

            scaler.scale(loss).backward()

            if step % grad_accum_steps == 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)

                scheduler.step(global_step)
                global_step += 1

            epoch_loss += loss.item() * grad_accum_steps

        avg_loss = epoch_loss / len(loader)
        LOGGER.info("Epoch %d | Loss %.6f", epoch + 1, avg_loss)

        torch.save(
            {"model": model.state_dict(), "loss": avg_loss},
            out_dir / "two_tower_last.pt",
        )

        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(
                {"model": model.state_dict(), "loss": best_loss},
                out_dir / "two_tower_best.pt",
            )


# ============================================================
# CLI
# ============================================================

def parse_mlp(s: str) -> Optional[List[int]]:
    return [int(x) for x in s.split(",")] if s else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train_path", required=True)
    p.add_argument("--out_dir", default="artifacts/two_tower")
    p.add_argument("--emb_dim", type=int, default=128)
    p.add_argument("--user_mlp", default="256,128")
    p.add_argument("--item_mlp", default="256,128")
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--batch_size", type=int, default=8192)
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--lr", type=float, default=2e-3)
    p.add_argument("--weight_decay", type=float, default=1e-5)
    p.add_argument("--temperature", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--grad_accum_steps", type=int, default=1)
    p.add_argument("--no_amp", action="store_true")
    p.add_argument("--no_compile", action="store_true")
    p.add_argument("--num_workers", type=int, default=4)

    args = p.parse_args()

    train_two_tower(
        train_path=args.train_path,
        out_dir=args.out_dir,
        emb_dim=args.emb_dim,
        user_mlp=parse_mlp(args.user_mlp),
        item_mlp=parse_mlp(args.item_mlp),
        dropout=args.dropout,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        temperature=args.temperature,
        seed=args.seed,
        amp=not args.no_amp,
        grad_accum_steps=args.grad_accum_steps,
        compile_model=not args.no_compile,
        num_workers=args.num_workers,
        resume_from=None,
    )


if __name__ == "__main__":
    main()
