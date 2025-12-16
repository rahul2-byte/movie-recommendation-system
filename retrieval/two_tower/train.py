"""
Two-Tower Retrieval Training Script (Production-Grade)

Responsibilities:
- Load split interaction data
- Remap user/item IDs locally (Option A)
- Train Two-Tower model with in-batch InfoNCE loss
- AMP + gradient clipping
- Checkpoint best & last models
- Save ID maps for traceability

NO feature merges.
NO dense item matrices.
SAFE for MovieLens-25M scale.
"""

import argparse
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

from model import TwoTower

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)


# -------------------------------------------------
# Reproducibility
# -------------------------------------------------
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# -------------------------------------------------
# Dataset
# -------------------------------------------------
class InteractionDataset(Dataset):
    """Yields (user_idx, item_idx) positive pairs."""

    def __init__(self, df: pd.DataFrame):
        self.users = torch.from_numpy(
            df["userId"].to_numpy(dtype=np.int64, copy=True)
        )
        self.items = torch.from_numpy(
            df["movieId"].to_numpy(dtype=np.int64, copy=True)
        )

    def __len__(self) -> int:
        return self.users.size(0)

    def __getitem__(self, idx: int):
        return self.users[idx], self.items[idx]


# -------------------------------------------------
# Loss
# -------------------------------------------------
def info_nce_loss(
    user_emb: torch.Tensor,
    item_emb: torch.Tensor,
    temperature: float,
) -> torch.Tensor:
    """
    Symmetric in-batch InfoNCE.
    """
    sim = torch.matmul(user_emb, item_emb.t()) / temperature
    targets = torch.arange(sim.size(0), device=sim.device)

    loss_u = torch.nn.functional.cross_entropy(sim, targets)
    loss_i = torch.nn.functional.cross_entropy(sim.t(), targets)
    return 0.5 * (loss_u + loss_i)


# -------------------------------------------------
# Training
# -------------------------------------------------
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
    resume_from: Optional[str],
) -> None:
    set_seed(seed)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_cuda = device == "cuda"

    LOGGER.info("Using device: %s", device)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # Load split interactions
    # -------------------------------------------------
    LOGGER.info("Loading training interactions: %s", train_path)
    df = pd.read_parquet(train_path)

    # -------------------------------------------------
    # Local remapping (Option A)
    # -------------------------------------------------
    user_codes = pd.Categorical(df["userId"])
    item_codes = pd.Categorical(df["movieId"])

    df["userId"] = user_codes.codes.astype("int64")
    df["movieId"] = item_codes.codes.astype("int64")

    num_users = int(user_codes.categories.size)
    num_items = int(item_codes.categories.size)

    LOGGER.info("Remapped users=%d items=%d", num_users, num_items)

    # Save ID maps (IMPORTANT)
    with open(out_dir / "id_maps.json", "w") as f:
        json.dump(
            {
                "user_id_map": user_codes.categories.tolist(),
                "item_id_map": item_codes.categories.tolist(),
            },
            f,
        )

    # -------------------------------------------------
    # Save model metadata (REQUIRED for embedding export)
    # -------------------------------------------------
    meta = {
        "num_users": int(num_users),
        "num_items": int(num_items),
        "emb_dim": int(emb_dim),
        "user_mlp": user_mlp,
        "item_mlp": item_mlp,
        "dropout": float(dropout),
        # IMPORTANT: this preserves original item ID order
        "item_id_map": item_codes.categories.tolist(),
    }

    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # -------------------------------------------------
    # DataLoader
    # -------------------------------------------------
    dataset = InteractionDataset(df)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,           # Windows-safe
        pin_memory=use_cuda,
        drop_last=True,
    )

    # -------------------------------------------------
    # Model
    # -------------------------------------------------
    model = TwoTower(
        num_users=num_users,
        num_items=num_items,
        emb_dim=emb_dim,
        user_mlp=user_mlp,
        item_mlp=item_mlp,
        dropout=dropout,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay,
    )

    scaler = torch.amp.GradScaler(device, enabled=(amp and use_cuda))

    best_loss = float("inf")
    start_epoch = 0

    # -------------------------------------------------
    # Resume (optional)
    # -------------------------------------------------
    if resume_from and Path(resume_from).exists():
        LOGGER.info("Resuming from checkpoint: %s", resume_from)
        ckpt = torch.load(resume_from, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        best_loss = ckpt["best_loss"]
        start_epoch = ckpt["epoch"] + 1

    # -------------------------------------------------
    # Training loop
    # -------------------------------------------------
    LOGGER.info(
        "Training started | epochs=%d batch_size=%d steps/epoch=%d",
        epochs,
        batch_size,
        len(loader),
    )

    total_steps = len(loader)
    total_examples = len(dataset)

    global_step = 0
    seen_examples = 0

    for epoch in range(start_epoch, epochs):
        model.train()
        epoch_loss = 0.0
        t0 = time.time()

        LOGGER.info(
            "Epoch %d/%d started",
            epoch + 1,
            epochs,
        )

        for step, (users, items) in enumerate(loader, start=1):
            users = users.to(device, non_blocking=True)
            items = items.to(device, non_blocking=True)

            batch_size_actual = users.size(0)
            seen_examples += batch_size_actual
            global_step += 1

            optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast(
                device_type=device,
                enabled=(amp and use_cuda),
            ):
                user_emb, item_emb = model(users, items)
                loss = info_nce_loss(user_emb, item_emb, temperature)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()

            loss_value = loss.item()
            epoch_loss += loss_value

            # -----------------------------------------
            # Step-level logging (every N steps)
            # -----------------------------------------
            if step % 100 == 0 or step == total_steps:
                LOGGER.info(
                    "Epoch %d/%d | Step %d/%d (%.1f%%) | "
                    "Seen %d/%d samples | "
                    "Batch loss = %.5f",
                    epoch + 1,
                    epochs,
                    step,
                    total_steps,
                    100.0 * step / total_steps,
                    seen_examples,
                    total_examples,
                    loss_value,
                )

        avg_epoch_loss = epoch_loss / total_steps
        epoch_time = time.time() - t0

        # -----------------------------------------
        # Epoch-level summary
        # -----------------------------------------
        LOGGER.info(
            "Epoch %d/%d completed | "
            "Avg loss = %.6f | "
            "Time = %.1fs",
            epoch + 1,
            epochs,
            avg_epoch_loss,
            epoch_time,
        )

        # -----------------------------------------
        # Checkpointing
        # -----------------------------------------
        ckpt = {
            "epoch": epoch,
            "best_loss": best_loss,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
        }
        torch.save(ckpt, out_dir / "two_tower_last.pt")

        if avg_epoch_loss < best_loss:
            best_loss = avg_epoch_loss
            ckpt["best_loss"] = best_loss
            torch.save(ckpt, out_dir / "two_tower_best.pt")
            LOGGER.info(
                "New best model saved | best_loss = %.6f",
                best_loss,
            )

    LOGGER.info("Saved training metadata to meta.json")
    LOGGER.info("Training finished successfully")


# -------------------------------------------------
# CLI
# -------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser("Two-Tower Retrieval Trainer")

    parser.add_argument("--train_path", required=True)
    parser.add_argument("--out_dir", default="artifacts/two_tower")

    parser.add_argument("--emb_dim", type=int, default=128)
    parser.add_argument("--user_mlp", type=str, default="256,128")
    parser.add_argument("--item_mlp", type=str, default="256,128")
    parser.add_argument("--dropout", type=float, default=0.1)

    parser.add_argument("--batch_size", type=int, default=4096)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-6)
    parser.add_argument("--temperature", type=float, default=0.07)

    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no_amp", action="store_true")
    parser.add_argument("--resume_from", type=str, default=None)

    return parser.parse_args()


def parse_mlp(s: str) -> Optional[List[int]]:
    if not s:
        return None
    return [int(x) for x in s.split(",")]


def main():
    args = parse_args()

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
        resume_from=args.resume_from,
    )


if __name__ == "__main__":
    main()
