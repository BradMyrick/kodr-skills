---
name: cs-rajbhandari-2019
description: Introduces ZeRO — sharding optimizer state (stage 1), gradients (stage 2), and parameters (stage 3) across data-parallel ranks to fit trillion-parameter training. Use when reasoning about memory sharding; pairs with ai-zero-fsdp.
version: 1.0.0
title: "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models"
authors: ["Samyam Rajbhandari", "Jeff Rasley", "Olatunji Ruwase", "Yuxiong He"]
venue: "arXiv:1910.02054"
year: 2019
url: "https://arxiv.org/abs/1910.02054"
related: ["ai-zero-fsdp", "cs-shoeybi-2019"]
---

# Skill: ZeRO — Sharding the Training State
## System Reference: Stage 1/2/3 Progressive Sharding (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Data-parallel training replicates the full **training state** on every GPU. ZeRO observes this is redundant: the state can be **partitioned** across DP ranks and gathered on demand with **no change to the math**.

For a model with $\Psi$ parameters in fp16 with fp32 Adam (state ≈ $16\Psi$ bytes):

| Stage | Partitioned | Per-GPU memory (vs DP) | Extra comm |
|---|---|---|---|
| **ZeRO-1** | optimizer state ($2\Psi$ fp32 moments) | $\frac{16\Psi}{N}\!\cdot\!4 + 2\Psi$ (~4× less) | ≈ same as DP |
| **ZeRO-2** | + gradients | $\frac{(2+2)\Psi}{N}\!\cdot\!4 + 2\Psi$ (~8× less) | ≈ same as DP |
| **ZeRO-3** | + parameters | $\frac{16\Psi}{N}$ (≈ $N$× less) | AllGather params per layer |

The key result: ZeRO-3 reduces per-GPU memory **linearly** with $N$, so total memory stays roughly constant as you scale — enabling a trillion-parameter model on thousands of GPUs. The cost is that ZeRO-3 must `AllGather` a layer's parameters before it computes and `ReduceScatter` its gradients after — extra traffic it overlaps with compute.

### 2. Operational Rules
* **Rule 1 (Progressive):** use ZeRO-2 by default (big memory win, DP-level comm); escalate to ZeRO-3 only when parameters themselves don't fit.
* **Rule 2 (Gather per layer, not per model):** shard at layer granularity so a gather is one layer.
* **Rule 3 (Overlap):** AllGather the next layer while computing the current.
* **Rule 4 (Math is unchanged):** ZeRO is an optimization, not an approximation — the update is bit-equivalent to DP.

### 3. Reference Implementation (Python)
```python
def per_gpu_bytes(Psi: float, stage: int, N: int, b: int = 16) -> float:
    optim, grad, param = 8 * Psi, 4 * Psi, 4 * Psi
    if stage >= 1: optim /= N
    if stage >= 2: grad /= N
    if stage >= 3: param /= N
    return optim + grad + param
```

### 4. Agent Execution Directives
* **When the optimizer state OOMs:** apply ZeRO-2; only if params OOM go to ZeRO-3 (FSDP).
* **Cite this paper** as the origin of parameter sharding that FSDP implements.
