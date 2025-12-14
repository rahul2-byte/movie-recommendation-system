# src/retrieval/two_tower/train.py
"""
Efficient training script for Two-Tower model.

Key features:
- In-batch InfoNCE (contrastive) loss (symmetrized).
- Mixed precision training with torch.cuda.amp (if GPU available).
- Checkpointing with best metric and resume support.
- Batch-size friendly: large batch sizes improve in-batch negatives.
- Controlled memory use: no dense item matrix materialized within training loop.

"""

import argparse
import json
import os
import random
import time
from typing import Optional

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

from model import TwoTower

# For reproducibility
def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    

class InteractionsDataset(torch.utils.data.Dataset):
    """
    Dataset that yields (user_idx, item_idx) positive pairs.
    Expects a dataframe with columns ['user_idx','item_idx','timestamp'] already encoded.
    """
    def __init__(self, df: pd.DataFrame):
        # force contiguous, owning copies
        u = df["userId"].to_numpy(dtype=np.int64, copy=True)
        i = df["movieId"].to_numpy(dtype=np.int64, copy=True)

        self.users = torch.from_numpy(u)           # torch.long
        self.items = torch.from_numpy(i)

    def __len__(self):
        return self.users.shape[0]

    def __getitem__(self, idx):
        return self.users[idx], self.items[idx]


def info_nce_loss(user_emb: torch.Tensor, item_emb: torch.Tensor, temperature: float = 0.07) -> torch.Tensor:
    """
    In-batch InfoNCE loss with symmetry.
    user_emb: (B, D), item_emb: (B, D), both normalized
    Loss = CE(sim_matrix / temp, target=range(B)) + CE(sim_matrix.T / temp, target=range(B)) / 2
    """
    # similarity matrix (B x B)
    sim = torch.matmul(user_emb, item_emb.t()) / temperature
    targets = torch.arange(sim.size(0), device=sim.device)
    loss_u = torch.nn.functional.cross_entropy(sim, targets)
    loss_i = torch.nn.functional.cross_entropy(sim.t(), targets)
    return (loss_u + loss_i) / 2.0


def train(
    ratings_csv: str,
    num_users: int,
    num_items: int,
    out_dir: str,
    emb_dim: int = 128,
    user_mlp: Optional[str] = None,
    item_mlp: Optional[str] = None,
    dropout: float = 0.1,
    batch_size: int = 4096,
    epochs: int = 6,
    lr: float = 1e-3,
    weight_decay: float = 1e-6,
    device: Optional[str] = None,
    resume_from: Optional[str] = None,
    amp: bool = True,
):
    """
    Train loop with mixed precision and stability features.
    """

    set_seed(42)

    use_cuda = torch.cuda.is_available()
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] using device: {device}")

    os.makedirs(out_dir, exist_ok=True)

    # Load interactions CSV (expects preprocessed user_idx/item_idx)
    df = pd.read_csv(ratings_csv, usecols=["userId", "movieId", "timestamp"])

    # Ensure contiguous 0..N-1 mapping here (robust)
    user_codes = pd.Categorical(df["userId"])
    item_codes = pd.Categorical(df["movieId"])
    df["userId"]  = user_codes.codes.astype("int64")
    df["movieId"] = item_codes.codes.astype("int64")
    num_users = int(user_codes.categories.size)
    num_items = int(item_codes.categories.size)
    print(f"[remap] num_users={num_users} num_items={num_items}")

    # optional: shuffle by timestamp? we keep temporal ordering at split time earlier
    ds = InteractionsDataset(df)
    loader = DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,  # ← start with 0 on Windows to rule out MP issues
        pin_memory=use_cuda,         # True only if CUDA
        drop_last=True,
        persistent_workers=False,       # must be False when num_workers=0
        prefetch_factor=None,           # PyTorch ignores when num_workers=0
    )

    # parse mlp strings like "256,128" into lists
    def parse_mlp(s):
        if not s:
            return None
        return [int(x) for x in s.split(",") if x.strip()]

    user_mlp_list = parse_mlp(user_mlp)
    item_mlp_list = parse_mlp(item_mlp)

    model = TwoTower(
        num_users=num_users,
        num_items=num_items,
        emb_dim=emb_dim,
        user_mlp=user_mlp_list,
        item_mlp=item_mlp_list,
        dropout=dropout,
    )
    model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scaler = torch.cuda.amp.GradScaler(enabled=(amp and torch.cuda.is_available()))

    start_epoch = 0
    best_loss = float("inf")

    # resume checkpointing
    if resume_from and os.path.exists(resume_from):
        print(f"[train] loading checkpoint {resume_from}")
        ckpt = torch.load(resume_from, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt.get("epoch", 0) + 1
        best_loss = ckpt.get("best_loss", best_loss)
        print(f"[train] resumed from epoch {start_epoch}, best_loss={best_loss}")

    # training loop
    print(f"[train] start training epochs={epochs}, batch={batch_size}, loader_len={len(loader)}")
    global_step = 0
    for epoch in range(start_epoch, epochs):
        model.train()
        epoch_loss = 0.0
        t0 = time.time()
        print(f"Epoch {epoch+1}/{epochs}")
        for batch_idx, (batch_users, batch_items) in enumerate(loader):
            batch_users = batch_users.to(device, non_blocking=True)
            batch_items = batch_items.to(device, non_blocking=True)

            # Debug guard (optional)
            if (batch_users.min() < 0 or batch_users.max() >= num_users or
                batch_items.min() < 0 or batch_items.max() >= num_items):
                print("[bad-batch] user range:", int(batch_users.min()), int(batch_users.max()),
                    "item range:", int(batch_items.min()), int(batch_items.max()),
                    "expected:", num_users, num_items)
                raise RuntimeError("Embedding index out of range in batch.")

            optimizer.zero_grad()

            scaler = torch.amp.GradScaler(device, enabled=(amp and use_cuda))
            autocast_ctx = torch.amp.autocast(device_type=device, enabled=(amp and use_cuda))
            with autocast_ctx:
                user_emb, item_emb = model(batch_users, batch_items) # (B, D)
                loss = info_nce_loss(user_emb, item_emb, temperature=0.07)

            scaler.scale(loss).backward()
            # gradient clipping for stability on large batches
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(optimizer)
            scaler.update()

            loss_item = loss.item()
            epoch_loss += loss_item
            global_step += 1

            if global_step % 100 == 0:
                avg_loss = epoch_loss / global_step
                print(f"  Batch {batch_idx+1}/{len(loader)} - loss: {loss_item:.4f}, avg_loss: {avg_loss:.4f}")

        epoch_time = time.time() - t0
        avg_epoch_loss = epoch_loss / len(loader)
        print(f"[train] epoch={epoch+1} avg_loss={avg_epoch_loss:.6f} time={epoch_time:.1f}s")

        # checkpoint every epoch (keeps last and best)
        ckpt = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "best_loss": best_loss,
        }
        last_path = os.path.join(out_dir, "two_tower_last.pt")
        torch.save(ckpt, last_path)

        if avg_epoch_loss < best_loss:
            best_loss = avg_epoch_loss
            best_path = os.path.join(out_dir, "two_tower_best.pt")
            ckpt["best_loss"] = best_loss
            torch.save(ckpt, best_path)
            print(f"[train] saved new best model to {best_path}")

    print("[train] finished training")

# local function to call train method and give all the params
def local_test_debug():

    ratings_csv = "../ml-25m/ratings.csv"
    num_users =162541
    num_items = 59047
    out_dir = "training/"
    emb_dim = 264
    user_mlp = item_mlp = "256,128"
    dropout = 0.1
    batch_size = 4096
    epochs = 10


    train(
        ratings_csv,
        num_users,
        num_items,
        out_dir,
        emb_dim,
        user_mlp,
        item_mlp,
        dropout,
        batch_size,
        epochs
    )


if __name__ == "__main__":

    # Local testing/debugging
    local_test_debug()
