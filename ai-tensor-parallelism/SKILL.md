---
name: ai-tensor-parallelism
description: Tensor & sequence parallelism — Megatron-style column/row weight splitting, the all-reduce/all-gather placement, and sequence parallelism for long context. Use when a single layer won't fit on one GPU or you need intra-layer parallelism. NOT the first choice — prefer DP/ZeRO (ai-parallelism-overview).
version: 1.0.0
---

# Skill: Tensor & Sequence Parallelism (Megatron)
## System Reference: Intra-Layer Weight Splitting + Sequence Sharding (RFC-Style Engineering Spec)

### 1. Core Model
**Tensor parallelism (TP)** splits a single layer's **weight matrices** across GPUs so each holds a slice and they cooperate per forward/backward. Megatron-LM exploits the structure of the two linear layers in a Transformer block to place the collective comms cleverly.

**Column-parallel linear.** Split $W$ by columns: $W = [W_1 \ldots W_N]$, each rank holds $W_i$; output $Y_i = X W_i$ is a **slice of the output columns** — no comm on the forward into it. Each rank applies its own nonlinearity locally.

**Row-parallel linear.** Split $W$ by rows: each rank holds $W_i$ and computes $Y_i = X_i W_i$ on its slice of activations, then **AllReduce** sums the partials: $Y = \sum_i Y_i$. This is where TP inserts a collective.

**The Megatron MLP trick** — pair column-parallel (first linear) with row-parallel (second linear) so the **nonlinearity (GELU) happens on the sharded columns** and there's exactly **one AllReduce per MLP block** (and one per attention block). That minimal-comm placement is the whole art of TP.

**Sequence parallelism (SP).** For long contexts, also shard the **sequence dimension** in the parts that don't need TP (LayerNorm/Dropout), using AllGather before and ReduceScatter after the TP regions. Cuts activation memory proportional to the TP degree — essential past 8k–32k tokens.

### 2. Operational Rules
* **Rule 1 (TP is intra-node only):** it inserts a collective every layer; keep it on NVLink-connected GPUs (≤ node size), never across slow inter-node links.
* **Rule 2 (Column-then-row, one AllReduce per block):** pair the two splits so the nonlinearity is local and the block needs exactly one AllReduce.
* **Rule 3 (Sequence-parallel for long context):** shard the sequence in the non-TP regions to cut activation memory linearly with TP degree.
* **Rule 4 (TP degree must divide hidden dim):** $H$ must be divisible by the TP degree or the column split is uneven.
* **Rule 5 (Cost is one AllReduce/AllGather per block):** TP trades activation comm for the ability to fit huge layers; quantify it against the roofline.

### 3. Reference Implementation (Python — column/row parallel linear)
```python
import numpy as np

def column_parallel_linear(X: np.ndarray, W_shards: list[np.ndarray]) -> list[np.ndarray]:
    """Each rank holds W_i (columns); outputs Y_i = X @ W_i — no comm here (Rule 2)."""
    return [X @ Wi for Wi in W_shards]

def row_parallel_linear(Y_shards: list[np.ndarray], V_shards: list[np.ndarray]) -> np.ndarray:
    """Each rank holds V_i (rows); Z_i = Y_i @ V_i; AllReduce-sums the partials (Rule 2)."""
    partials = [Yi @ Vi for Yi, Vi in zip(Y_shards, V_shards)]
    out = np.zeros_like(partials[0])
    for p in partials: out += p                # the single AllReduce of the block
    return out

def megatron_mlp(X, Wcol_shards, Vrow_shards, gelu):
    """Column-parallel -> GELU (local on sharded cols) -> row-parallel -> AllReduce."""
    Y = column_parallel_linear(X, Wcol_shards)          # sharded columns of output
    Y = [gelu(y) for y in Y]                            # nonlinearity is LOCAL (the trick)
    return row_parallel_linear(Y, Vrow_shards)          # one AllReduce total (Rule 2)

if __name__ == "__main__":
    H, tp = 8, 2
    X = np.random.randn(4, H)
    W_full = np.random.randn(H, H); V_full = np.random.randn(H, H)
    W_shards = np.split(W_full, tp, axis=1)             # column-parallel
    V_shards = np.split(V_full, tp, axis=0)             # row-parallel
    gelu = lambda z: 0.5 * z * (1 + np.tanh(np.sqrt(2/np.pi) * (z + 0.044715 * z**3)))
    tp_out = megatron_mlp(X, W_shards, V_shards, gelu)
    ref = gelu(X @ W_full) @ V_full                      # the math the 2 GPUs are computing together
    assert np.allclose(tp_out, ref, atol=1e-4), "TP must equal the unsharded math"
    print("tensor-parallel output matches single-GPU math")
```

### 4. Agent Execution Directives
* **When a single layer won't fit:** reach for TP, kept intra-node (NVLink), with column-then-row placement (Rules 1–2).
* **For long context:** add sequence parallelism to slash activation memory (Rule 3).
* **Always verify** the sharded math equals the unsharded reference numerically (the demo asserts it).
