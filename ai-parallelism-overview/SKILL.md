---
name: ai-parallelism-overview
description: The map of distributed-training parallelism — data, tensor, pipeline, sequence, expert, ZeRO — and how they compose into 3D/4D/5D parallelism plus cluster scheduling. Use FIRST for any training/inference parallelism question before going deep into a specific axis. NOT a deep-dive into any single axis.
version: 1.0.0
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

@dataclass
class ModelSpec:
    params_B: float        # billions of parameters
    batch_tokens: int
    seq_len: int
    hidden: int
    layers: int

def bytes_for(params_B: float, dtype_bytes: int = 2, optim_factor: float = 12) -> float:
    """fp16/bf16 weights + Adam state + grads ~= optim_factor * params bytes (ZeRO-0)."""
    return params_B * 1e9 * optim_factor * dtype_bytes / 2  # rule of thumb: ~12x params in fp16

def choose_axes(model: ModelSpec, gpu_mem_bytes: float, n_gpu: int, nvlink_group: int) -> dict:
    """Greedy: fit with DP+ZeRO; add TP intra-node if a layer still won't fit; PP across nodes last."""
    single = bytes_for(model.params_B)
    need = max(1, int(single // gpu_mem_bytes) + 1)        # Rule 1: how many GPUs to fit weights
    tp = 1
    if need > 1:
        tp = min(need, nvlink_group)                       # Rule 3: TP stays intra-node (NVLink)
    dp = max(1, n_gpu // tp)                                # Rule 4: product = N
    return {"DP": dp, "TP": tp, "PP": 1, "EP": 1,
            "shard": f"ZeRO stage {min(3, need)}", "fits": (dp * tp) <= n_gpu}

if __name__ == "__main__":
    m = ModelSpec(70, 2048, 2048, 8192, 80)
    print("70B on 8x80GB:", choose_axes(m, gpu_mem_bytes=80*2**30, n_gpu=8, nvlink_group=8))
    print("~bytes for 70B (fp16+Adam):", f"{bytes_for(70)/2**30:.0f} GiB")
```

### 4. Agent Execution Directives
* **For any "how do I train X on Y GPUs":** compute the memory first, then return a parallelism config with the product of axes = GPU count and axes mapped to topology (Rules 1, 3, 4).
* **Always quantify communication:** cite the roofline / collective volume, not "it should be fast."
* **Default to DP+ZeRO/FSDP;** escalate to TP/PP only with a measured reason.
