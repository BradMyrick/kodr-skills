---
name: ai-memory-analysis
description: Memory accounting for large-model training — weights, optimizer state, activations, the KV cache — and the levers (recomputation, offloading, sharding) to fit. Use when a model OOMs or when sizing a config. Pair with ai-zero-fsdp / ai-parallelism-overview.
version: 1.0.0
---

# Skill: Training/Inference Memory Analysis
## System Reference: The Memory Budget + Its Levers (RFC-Style Engineering Spec)

### 1. Core Model
GPU memory is the binding constraint in most LLM work. The budget has three parts:

$$\text{memory} = \underbrace{W}_{\text{weights}} + \underbrace{O}_{\text{optimizer/grad state}} + \underbrace{A(b, s, L, h)}_{\text{activations}}$$

* **Weights** $W$: $P \cdot b_w$ bytes ($b_w=2$ for bf16, ~1 for fp8, 4 for fp32).
* **Optimizer state** $O$: ~$12\,P$ bytes for fp16+Adam (m, v, master) — dominates $W$; this is what ZeRO shards (`ai-zero-fsdp`).
* **Activations** $A$: roughly $L \cdot s \cdot b \cdot h \cdot \gamma$ bytes — **scales with batch×sequence×layers**. For a Transformer, $\gamma$ captures the per-layer factor (~34 for the standard block in fp16 without checkpointing, per the Megatron derivation). Activations are the lever during training; the **KV cache** (see `ai-inference-serving`) dominates during inference.

**The levers (in order of cost):**
1. **Mixed precision** (bf16/fp8): halves/quarters weights and activations. Cheapest win.
2. **Activation recomputation** (gradient checkpointing): don't store all forward activations; recompute them in backward. Cuts $A$ by $\sqrt{L}$-ish (selective) to $L$ (full), at ~33% extra compute. The classic memory↔compute trade.
3. **ZeRO/FSDP**: shard $O$ (and $W$ at stage 3) across GPUs.
4. **Offloading**: move $O$ or $W$ to CPU/NVMe (slow, last resort).
5. **Tensor/sequence/pipeline parallelism**: split $W$ and $A$ across GPUs.

### 2. Operational Rules
* **Rule 1 (Account before optimizing):** compute $W + O + A$; you can't fix an OOM you haven't budgeted.
* **Rule 2 (Mixed precision first):** bf16 weights/activations + fp32 master is the baseline; fp8 where supported.
* **Rule 3 (Recompute for activations):** when activations OOM, gradient checkpointing is the cheapest lever (memory for ~33% compute).
* **Rule 4 (Shard the state):** optimizer state is the biggest chunk — ZeRO-2/3 or FSDP it.
* **Rule 5 (Sequence length drives activations):** long context multiplies $A$; use sequence parallelism / attention sparsity / chunked attention.
* **Rule 6 (Inference ≠ training):** inference has no optimizer state but a growing **KV cache**; size it per concurrent request (see `ai-inference-serving`).

### 3. Reference Implementation (Python — memory estimator with levers)
```python
def total_memory(P: float, L: int, s: int, b: int, h: int,
                 bytes_w: int = 2, optimizer_bytes: int = 12, gamma: int = 34,
                 recompute: bool = False, zero_stage: int = 0, n_gpu: int = 1) -> float:
    """Per-GPU bytes for training a Transformer (Rule 1)."""
    W = P * bytes_w
    O = P * optimizer_bytes
    if zero_stage >= 1: O /= n_gpu                          # Rule 4: shard optimizer
    if zero_stage >= 3: W /= n_gpu                          # shard params too
    A = L * s * b * h * gamma * 2                           # activation bytes (bf16)
    if recompute: A /= 10                                   # Rule 3: recompute ~sqrt(L) memory
    return W + O + A

def fits(mem_bytes: float, gpu_bytes: float) -> bool:
    return mem_bytes <= gpu_bytes

if __name__ == "__main__":
    P, L, s, b, h = 70e9, 80, 2048, 8, 8192
    for recomp in (False, True):
        for z in (0, 2):
            m = total_memory(P, L, s, b, h, recompute=recomp, zero_stage=z, n_gpu=8)
            print(f"recompute={recomp} zero={z}: {m/2**30:7.1f} GiB/GPU  fits-80GB={fits(m,80*2**30)}")
```

### 4. Agent Execution Directives
* **On OOM:** compute the budget first; apply levers in cost order (precision → recompute → shard → offload).
* **For long-context:** activations dominate; use sequence parallelism + recomputation + (chunked/flash) attention.
* **For inference:** size the KV cache (per-request × concurrency), not the optimizer state.
