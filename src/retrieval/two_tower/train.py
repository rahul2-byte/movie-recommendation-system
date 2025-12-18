"""
Optimized Two-Tower Retrieval Training Script

Key Optimizations:
1. Vectorized negative sampling with in-batch negatives
2. Compiled model with torch.compile()
3. Optimized data loading with prefetching
4. Gradient accumulation for effective larger batches
5. Cosine annealing with warmup
6. Mixed precision training (bf16 on modern GPUs)
7. Optimized loss computation
8. Smart checkpointing strategy
"""

import argparse
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from model import TwoTower

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# -------------------------------------------------
# OPTIMIZATION 1: Efficient Dataset with Caching
# -------------------------------------------------
class OptimizedInteractionDataset(Dataset):
    """
    Pre-converts to tensors and keeps in memory.
    Eliminates repeated conversions in __getitem__.
    """
    def __init__(self, df: pd.DataFrame):
        # Convert once, keep as tensors
        self.users = torch.from_numpy(df["userId"].values.astype(np.int64))
        self.items = torch.from_numpy(df["movieId"].values.astype(np.int64))
        
    def __len__(self) -> int:
        return len(self.users)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.users[idx], self.items[idx]


# -------------------------------------------------
# OPTIMIZATION 2: Optimized InfoNCE Loss
# -------------------------------------------------
@torch.jit.script
def optimized_info_nce_loss(
    user_emb: torch.Tensor,
    item_emb: torch.Tensor,
    temperature: float,
) -> torch.Tensor:
    """
    Optimizations:
    - JIT compilation for faster execution
    - Fused operations where possible
    - Efficient memory layout
    """
    # Normalize embeddings for numerical stability
    user_emb = F.normalize(user_emb, p=2.0, dim=1)
    item_emb = F.normalize(item_emb, p=2.0, dim=1)
    
    # Compute similarity matrix
    logits = torch.matmul(user_emb, item_emb.t()) / temperature
    
    # Targets are diagonal (positive pairs)
    batch_size = logits.size(0)
    labels = torch.arange(batch_size, device=logits.device, dtype=torch.long)
    
    # Symmetric loss
    loss_user = F.cross_entropy(logits, labels)
    loss_item = F.cross_entropy(logits.t(), labels)
    
    return (loss_user + loss_item) * 0.5


# -------------------------------------------------
# OPTIMIZATION 3: Learning Rate Schedule
# -------------------------------------------------
class CosineWarmupScheduler:
    """Cosine annealing with linear warmup."""
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
        self.base_lrs = [group['lr'] for group in optimizer.param_groups]
        
    def step(self, current_step: int):
        if current_step < self.warmup_steps:
            # Linear warmup
            lr_mult = current_step / max(1, self.warmup_steps)
        else:
            # Cosine annealing
            progress = (current_step - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
            lr_mult = self.min_lr_ratio + (1 - self.min_lr_ratio) * 0.5 * (1 + np.cos(np.pi * progress))
        
        for param_group, base_lr in zip(self.optimizer.param_groups, self.base_lrs):
            param_group['lr'] = base_lr * lr_mult


# -------------------------------------------------
# OPTIMIZATION 4: Main Training Function
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
    grad_accum_steps: int = 1,
    compile_model: bool = False,
    num_workers: int = 4,
    use_bf16: bool = True,
) -> None:
    set_seed(seed)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"
    
    # Determine dtype for mixed precision
    if amp and torch.cuda.is_available():
        device_index = torch.cuda.current_device()

        if use_bf16 and torch.cuda.get_device_properties(device_index).major >= 8:
            amp_dtype = torch.bfloat16
            LOGGER.info("Using bfloat16 mixed precision")
        else:
            amp_dtype = torch.float16
            LOGGER.info("Using float16 mixed precision")
    else:
        amp_dtype = None
    
    LOGGER.info("Device: %s | AMP: %s", device, amp and use_cuda)
    
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------
    # Load and preprocess data
    # -------------------------------------------------
    LOGGER.info("Loading training data: %s", train_path)
    df = pd.read_csv(train_path)
    
    # Local remapping
    user_codes = pd.Categorical(df["userId"])
    item_codes = pd.Categorical(df["movieId"])
    
    df["userId"] = user_codes.codes.astype(np.int64)
    df["movieId"] = item_codes.codes.astype(np.int64)
    
    num_users = len(user_codes.categories)
    num_items = len(item_codes.categories)
    
    LOGGER.info("Users: %d | Items: %d | Interactions: %d", 
                num_users, num_items, len(df))
    
    # Save metadata
    meta = {
        "num_users": num_users,
        "num_items": num_items,
        "emb_dim": emb_dim,
        "user_mlp": user_mlp,
        "item_mlp": item_mlp,
        "dropout": dropout,
        "item_id_map": item_codes.categories.tolist(),
    }
    
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    
    with open(out_dir / "id_maps.json", "w") as f:
        json.dump({
            "user_id_map": user_codes.categories.tolist(),
            "item_id_map": item_codes.categories.tolist(),
        }, f)
    
    # -------------------------------------------------
    # OPTIMIZATION 5: Optimized DataLoader
    # -------------------------------------------------
    dataset = OptimizedInteractionDataset(df)
    
    # Use more workers for data loading parallelism
    actual_num_workers = num_workers if use_cuda else 0
    
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=actual_num_workers,
        pin_memory=use_cuda,
        drop_last=True,
        persistent_workers=actual_num_workers > 0,  # Keep workers alive
        prefetch_factor=2 if actual_num_workers > 0 else None,  # Prefetch batches
    )
    
    # -------------------------------------------------
    # Model initialization
    # -------------------------------------------------
    model = TwoTower(
        num_users=num_users,
        num_items=num_items,
        emb_dim=emb_dim,
        user_mlp=user_mlp,
        item_mlp=item_mlp,
        dropout=dropout,
    ).to(device)
    
    # OPTIMIZATION 6: Compile model (PyTorch 2.0+)
    if compile_model and hasattr(torch, 'compile'):
        try:
            if torch.cuda.is_available() and os.name != "nt":
                LOGGER.info("Compiling model with torch.compile()...")
                model = torch.compile(model)
                LOGGER.info("Model compilation successful")
            else:
                LOGGER.warning("torch.compile disabled on Windows")
        except Exception as e:
            LOGGER.warning("Model compilation failed: %s", e)
    
    # -------------------------------------------------
    # Optimizer with fused implementation
    # -------------------------------------------------
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay,
        fused=use_cuda,  # Faster fused kernel on CUDA
    )
    
    # Learning rate scheduler
    total_steps = len(loader) * epochs // grad_accum_steps
    warmup_steps = min(500, total_steps // 10)
    scheduler = CosineWarmupScheduler(optimizer, warmup_steps, total_steps)
    
    # Mixed precision scaler
    scaler = torch.amp.GradScaler(device.type, enabled=(amp and use_cuda))
    
    best_loss = float("inf")
    start_epoch = 0
    global_step = 0
    
    # Resume checkpoint
    if resume_from and Path(resume_from).exists():
        LOGGER.info("Resuming from: %s", resume_from)
        ckpt = torch.load(resume_from, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        best_loss = ckpt.get("best_loss", float("inf"))
        start_epoch = ckpt.get("epoch", 0) + 1
        global_step = ckpt.get("global_step", 0)
    
    # -------------------------------------------------
    # Training Loop
    # -------------------------------------------------
    LOGGER.info("Starting training | Epochs: %d | Batch size: %d | Grad accum: %d",
                epochs, batch_size, grad_accum_steps)
    LOGGER.info("Effective batch size: %d", batch_size * grad_accum_steps)
    
    for epoch in range(start_epoch, epochs):
        model.train()
        epoch_loss = 0.0
        epoch_steps = 0
        t0 = time.time()
        
        optimizer.zero_grad(set_to_none=True)
        
        for step, (users, items) in enumerate(loader, start=1):
            users = users.to(device, non_blocking=True)
            items = items.to(device, non_blocking=True)
            
            # Forward pass with autocast
            with torch.amp.autocast(device_type=device.type, dtype=amp_dtype, enabled=(amp and use_cuda)):
                user_emb, item_emb = model(users, items)
                loss = optimized_info_nce_loss(user_emb, item_emb, temperature)
                loss = loss / grad_accum_steps  # Scale loss for accumulation
            
            # Backward pass
            scaler.scale(loss).backward()
            
            # Update weights every grad_accum_steps
            if step % grad_accum_steps == 0 or step == len(loader):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                
                # Update learning rate
                scheduler.step(global_step)
                global_step += 1
            
            epoch_loss += loss.item() * grad_accum_steps
            epoch_steps += 1
            
            # Logging
            if step % 100 == 0:
                current_lr = optimizer.param_groups[0]['lr']
                LOGGER.info(
                    "Epoch %d/%d | Step %d/%d | Loss: %.5f | LR: %.2e",
                    epoch + 1, epochs, step, len(loader), 
                    loss.item() * grad_accum_steps, current_lr
                )
        
        avg_loss = epoch_loss / epoch_steps
        epoch_time = time.time() - t0
        
        LOGGER.info(
            "Epoch %d/%d done | Avg loss: %.6f | Time: %.1fs | Throughput: %.0f samples/s",
            epoch + 1, epochs, avg_loss, epoch_time,
            len(dataset) / epoch_time
        )
        
        # -------------------------------------------------
        # OPTIMIZATION 7: Smart Checkpointing
        # -------------------------------------------------
        # Save last checkpoint every epoch
        ckpt = {
            "epoch": epoch,
            "global_step": global_step,
            "best_loss": best_loss,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
        }
        torch.save(ckpt, out_dir / "two_tower_last.pt")
        
        # Save best checkpoint
        if avg_loss < best_loss:
            best_loss = avg_loss
            ckpt["best_loss"] = best_loss
            torch.save(ckpt, out_dir / "two_tower_best.pt")
            LOGGER.info("New best model | Loss: %.6f", best_loss)
    
    LOGGER.info("Training complete!")


# -------------------------------------------------
# CLI
# -------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser("Optimized Two-Tower Trainer")
    
    parser.add_argument("--train_path", required=True)
    parser.add_argument("--out_dir", default="artifacts/two_tower_optimized")
    
    parser.add_argument("--emb_dim", type=int, default=128)
    parser.add_argument("--user_mlp", type=str, default="256,128")
    parser.add_argument("--item_mlp", type=str, default="256,128")
    parser.add_argument("--dropout", type=float, default=0.1)
    
    parser.add_argument("--batch_size", type=int, default=8192)
    parser.add_argument("--grad_accum_steps", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-5)
    parser.add_argument("--temperature", type=float, default=0.05)
    
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no_amp", action="store_true")
    parser.add_argument("--no_compile", action="store_true")
    parser.add_argument("--num_workers", type=int, default=4)
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
        grad_accum_steps=args.grad_accum_steps,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        temperature=args.temperature,
        seed=args.seed,
        amp=not args.no_amp,
        compile_model=not args.no_compile,
        num_workers=args.num_workers,
        resume_from=args.resume_from,
    )


if __name__ == "__main__":
    main()