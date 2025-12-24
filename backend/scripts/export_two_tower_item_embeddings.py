#!/usr/bin/env python3
"""
Export item and user embeddings from a trained Two-Tower model.

Responsibilities:
- Load trained checkpoint
- Reconstruct model
- Compute item embeddings in batches
- Compute user embeddings in batches
- Persist embeddings + id map + metadata
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from retrieval.two_tower.model import TwoTower

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("export_two_tower_embeddings")


# ---------------------------------------------------------
# Item embedding export
# ---------------------------------------------------------
@torch.no_grad()
def export_item_embeddings(
    model: TwoTower,
    device: str,
    out_dir: Path,
    item_id_map: list[int],
    batch_size: int,
) -> None:
    model.eval()
    model.to(device)

    num_items = len(item_id_map)
    emb_dim = model.item_tower.id_emb.embedding_dim

    LOGGER.info("Exporting %d item embeddings (dim=%d)", num_items, emb_dim)

    embeddings = np.zeros((num_items, emb_dim), dtype=np.float32)

    for start in tqdm(range(0, num_items, batch_size), desc="export_items"):
        end = min(start + batch_size, num_items)
        item_indices = torch.arange(start, end, device=device)
        emb = model.encode_items(item_indices)
        embeddings[start:end] = emb.cpu().numpy()

    embeddings = np.ascontiguousarray(embeddings)

    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "item_embeddings.npy", embeddings)

    with open(out_dir / "item_id_map.json", "w") as f:
        json.dump(
            {int(item_id): idx for idx, item_id in enumerate(item_id_map)},
            f,
        )

    LOGGER.info("Item embeddings exported")


# ---------------------------------------------------------
# User embedding export  ✅ NEW
# ---------------------------------------------------------
@torch.no_grad()
def export_user_embeddings(
    model: TwoTower,
    device: str,
    out_dir: Path,
    user_id_map: list[int],
    batch_size: int,
) -> None:
    model.eval()
    model.to(device)

    num_users = len(user_id_map)
    emb_dim = model.user_tower.id_emb.embedding_dim

    LOGGER.info("Exporting %d user embeddings (dim=%d)", num_users, emb_dim)

    embeddings = np.zeros((num_users, emb_dim), dtype=np.float32)

    for start in tqdm(range(0, num_users, batch_size), desc="export_users"):
        end = min(start + batch_size, num_users)
        user_indices = torch.arange(start, end, device=device)
        emb = model.encode_users(user_indices)
        embeddings[start:end] = emb.cpu().numpy()

    embeddings = np.ascontiguousarray(embeddings)

    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "user_embeddings.npy", embeddings)

    LOGGER.info("User embeddings exported")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main(args: argparse.Namespace) -> None:
    device = args.device

    LOGGER.info("Loading checkpoint: %s", args.checkpoint)
    ckpt = torch.load(args.checkpoint, map_location=device)

    LOGGER.info("Loading training metadata: %s", args.meta)
    meta = json.load(open(args.meta, "r"))

    model = TwoTower(
        num_users=meta["num_users"],
        num_items=meta["num_items"],
        emb_dim=meta["emb_dim"],
        user_mlp=meta.get("user_mlp"),
        item_mlp=meta.get("item_mlp"),
        dropout=meta.get("dropout", 0.0),
    )

    model.load_state_dict(ckpt["model_state_dict"])
    id_maps = json.load(open(args.id_maps, "r"))

    out_dir = Path(args.out_dir)

    # -----------------------------
    # Export item embeddings
    # -----------------------------
    export_item_embeddings(
        model=model,
        device=device,
        out_dir=out_dir,
        item_id_map=id_maps["item_id_map"],
        batch_size=args.batch_size,
    )

    # -----------------------------
    # Export user embeddings
    # -----------------------------
    export_user_embeddings(
        model=model,
        device=device,
        out_dir=out_dir,
        user_id_map=id_maps["user_id_map"],
        batch_size=args.batch_size,
    )

    # -----------------------------
    # Metadata (single source)
    # -----------------------------
    metadata = {
        "model": "two_tower",
        "embedding_dim": int(meta["emb_dim"]),
        "num_items": int(meta["num_items"]),
        "num_users": int(meta["num_users"]),
        "normalized": True,
    }

    with open(out_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    LOGGER.info("Two-Tower embedding export completed")


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Export Two-Tower Embeddings")

    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--meta", required=True)
    parser.add_argument("--id_maps", required=True)

    parser.add_argument("--out_dir", default="models/two_tower")
    parser.add_argument("--batch_size", type=int, default=4096)
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
