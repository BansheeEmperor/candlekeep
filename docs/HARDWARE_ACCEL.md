# Hardware-Accelerated Inference

## Problem

The precise path cross-encoder ran CPU-only PyTorch inference, taking ~3s per query. Latency was capped by host hardware, not by the tool. The simple path (22–36ms) was unaffected since vector lookup dominates there.

## Solution

Auto-detect the best available compute device at startup and pass it through to both the bi-encoder (embeddings) and cross-encoder (reranker). Cache the cross-encoder as a singleton instead of re-instantiating per call.

**Files changed:** `config.py`, `embeddings.py`, `reranker.py`, `router.py`, `mcp/server.py`

**Configuration:** `CANDLEKEEP_DEVICE` env var (`auto`/`cpu`/`mps`/`cuda`), defaults to `auto`. PyTorch exposes both Nvidia and AMD GPUs as `device="cuda"` — no separate ROCm handling needed.

## Results

| Backend | Device | Simple path | Precise path |
|---------|--------|------------|-------------|
| PyTorch | CPU | 23ms | ~3000ms |
| PyTorch | MPS | 21ms | **130ms** (23.7x speedup) |

## MLX Evaluation

MLX native inference was benchmarked against MPS for the bi-encoder (bge-small):

| Backend | 5 queries | Per query |
|---------|----------|-----------|
| MPS (PyTorch) | 10.4ms | 2.1ms |
| MLX (native) | 6.0ms | 1.2ms (1.8x faster) |

MLX is 1.8x faster for embeddings, but the absolute gain is ~4ms on a 21ms operation. The cross-encoder (the actual bottleneck) has no MLX equivalent. ROI does not justify the integration cost.
