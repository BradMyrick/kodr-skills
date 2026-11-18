---
name: ai-parallelism-overview
description: The map of distributed-training parallelism — data, tensor, pipeline, sequence, expert, ZeRO — and how they compose into 3D/4D/5D parallelism plus cluster scheduling. Use FIRST for any training/inference parallelism question before going deep into a specific axis. NOT a deep-dive into any single axis.
version: 1.0.1
---

# Skill: Distributed-Training Parallelism Map
## System Reference: The Parallelism Axes + Their Composition (RFC-Style Engineering Spec)

### 1. Core Model
A model too large for one GPU, or a batch too big for one GPU's memory, must be split. There are six orthogonal **axes** of parallelism; production systems compose several at once (3D/4D/5D parallelism). Choosing the mix is a memory-vs-communication-vs-utilization optimization.

**The axes:**
| Axis | Splits | Comm each step | Skill |
|---|---|---|---|
| **Data (DP)** | the batch across GPUs | gradients (AllReduce) | `ai-data-parallelism` |
| **Tensor (TP)** | each weight matrix across GPUs | activations (AllReduce/AllGather) every layer | `ai-tensor-parallelism` |
| **Pipeline (PP)** | layers across GPUs (stages) | activations between stages | `ai-pipeline-parallelism` |
| **Sequence (SP)** | the sequence dim across GPUs | activations (AllGather/ReduceScatter) | `ai-tensor-parallelism` |
| **Expert (EP)** | MoE experts across GPUs | routed tokens (All-to-All) | `ai-mixture-of-experts` |
| **ZeRO/FSDP** | optimizer state / grad / params | sharded gather per layer | `ai-zero-fsdp` |

**Composition.** Real configs combine them: Megatron-LM = DP × TP × PP (3D); add ZeRO within DP and SP within TP for 4D/5D. The product of the axis degrees must equal the GPU count: $N = DP \cdot TP \cdot PP \cdot EP$.

**The fundamental trade-off:** every axis you add trades **memory** (you can fit a bigger model) for **communication** (more collective traffic) and **idle time** (pipeline bubbles, imbalance). The roofline (`ai-collective-comms`) tells you when communication dominates.

### 2. Operational Rules
* **Rule 1 (Start with the memory math):** compute the per-GPU memory for weights/activations/optimizer (`ai-memory-analysis`) before choosing axes; the axes are a means to fit, not a goal.
* **Rule 2 (Prefer DP + ZeRO/FSDP first):** data parallelism with sharding scales farthest with the least code; reach for TP/PP only when a single layer still won't fit.
* **Rule 3 (Match axes to the topology):** put high-bandwidth axes (TP) on NVLink-connected intra-node GPUs; put lower-comm axes (DP/PP/EP) across slower inter-node links.
* **Rule 4 (Product = GPU count):** $DP \cdot TP \cdot PP \cdot EP = N$; a mis-factorized config strands GPUs.
* **Rule 5 (Minimize the bubble):** pipeline parallelism idles GPUs during the fill/drain; use 1F1B/interleaving to shrink the bubble (Rule → `ai-pipeline-parallelism`).
* **Rule 6 (Gang-schedule for training):** a training job needs all its GPUs simultaneously; the scheduler must co-allocate them or throughput collapses.

### 3. Reference Implementation (Python — parallelism planner)
```python
from dataclasses import dataclass
from math import ceil

@dataclass
class ModelSpec:
    params_B: float        # billions of parameters

# bytes/param under mixed-precision Adam: bf16 weights + bf16 grads +
# fp32 master weights + fp32 Adam moments (see `ai-memory-analysis`)
W_BYTES, G_BYTES, O_BYTES = 2, 2, 12

def per_gpu_state_bytes(params_B: float, tp: int, pp: int, dp: int, zero: int) -> float:
    """Per-GPU weights+grads+optimizer bytes. TP/PP shard the model; ZeRO shards across DP ranks."""
    shard = tp * pp
    w = params_B * 1e9 * W_BYTES / shard
    g = params_B * 1e9 * G_BYTES / shard
    o = params_B * 1e9 * O_BYTES / shard
    if zero >= 1: o /= dp          # stage 1: optimizer state sharded over DP
    if zero >= 2: g /= dp          # stage 2: + grads
    if zero >= 3: w /= dp          # stage 3: + params (ZeRO-3 / FSDP)
    return w + g + o

def choose_axes(model: ModelSpec, gpu_mem_bytes: float, n_gpu: int, nvlink_group: int,
               act_headroom: float = 0.85) -> dict:
    """Rules 1-4: memory math first (1); prefer DP+ZeRO, TP only intra-node, PP last (2, 3); product == n_gpu (4)."""
    budget = gpu_mem_bytes * act_headroom   # Rule 1: reserve headroom for activations
    best, best_cost = None, None
    for zero in (0, 1, 2, 3):
        for tp in (1, 2, 4, 8):
            if tp > nvlink_group:           # Rule 3: TP stays on the NVLink island
                continue
            for pp in (1, 2, 4, 8):
                if n_gpu % (tp * pp):
                    continue
                dp = n_gpu // (tp * pp)     # Rule 4: DP * TP * PP == n_gpu
                if per_gpu_state_bytes(model.params_B, tp, pp, dp, zero) <= budget:
                    # Rule 2: cheapest comm first — ZeRO < TP < PP
                    cost = zero + 4 * (tp > 1) + 8 * (pp > 1)
                    if best_cost is None or cost < best_cost:
                        best, best_cost = {"DP": dp, "TP": tp, "PP": pp, "ZeRO": zero}, cost
    if best:
        return best
    # Nothing fits: report the floor — full ZeRO-3 sharding needs >= 16 bytes/param per GPU
    total = model.params_B * 1e9 * (W_BYTES + G_BYTES + O_BYTES)
    return {"fits": False, "min_gpus_zero3": ceil(total / budget)}

if __name__ == "__main__":
    g80 = 80 * 2**30
    print("7B  on  8x80GB:", choose_axes(ModelSpec(7),  g80, 8, 8))    # DP=8, ZeRO-1
    print("70B on  8x80GB:", choose_axes(ModelSpec(70), g80, 8, 8))    # fits: False — do the math first
    print("70B on 16x80GB:", choose_axes(ModelSpec(70), g80, 16, 8))   # DP=16, ZeRO-3
    print("70B on 64x80GB:", choose_axes(ModelSpec(70), g80, 64, 8))   # DP=64, ZeRO-3
```

### 4. Agent Execution Directives
* **For any "how do I train X on Y GPUs":** compute the memory first, then return a parallelism config with the product of axes = GPU count and axes mapped to topology (Rules 1, 3, 4).
* **Always quantify communication:** cite the roofline / collective volume, not "it should be fast."
* **Default to DP+ZeRO/FSDP;** escalate to TP/PP only with a measured reason.
