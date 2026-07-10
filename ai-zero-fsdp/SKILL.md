---
name: ai-zero-fsdp
description: Memory sharding for data-parallel training — ZeRO stages 1/2/3 (optimizer state / gradient / parameter sharding) and PyTorch FSDP. Use when the model fits its activations but not its full training state on one GPU. NOT intra-layer splitting — use ai-tensor-parallelism.
version: 1.0.0
---

# Skill: ZeRO & FSDP — Sharding the Training State
## System Reference: Sharded Optimizer/Gradient/Parameter State (RFC-Style Engineering Spec)

### 1. Core Model
Training a model stores far more than weights. For a model with $P$ parameters in fp16 with fp32 Adam state, the **training state** is ~16 bytes/param:
* Optimizer state (Adam m, v in fp32): ~8 bytes/param
* Gradients (fp32): ~4 bytes/param
* Parameters (fp16 weights + fp32 master copy): ~4–6 bytes/param

A 70B model needs ~1.1 TB of state — impossible on one GPU. **ZeRO** shards this state across data-parallel ranks so each holds $1/N$ of it, gathering it on demand:

| Stage | Sharded | Memory (vs baseline) | Comm cost |
|---|---|---|---|
| **ZeRO-1** | optimizer state | ~4× less | same as DP |
| **ZeRO-2** | + gradients | ~8× less | same as DP |
| **ZeRO-3** | + parameters | ~N× less | more (gather params per layer) |

**FSDP (Fully Sharded Data Parallel)** is PyTorch's ZeRO-3: each rank holds a shard of parameters; before a layer's forward/backward it **AllGathers** the full params, computes, then **discards** them (freeing memory), and **ReduceScatters** the gradients. This trades extra param-gather traffic for the ability to fit models far larger than one GPU.

**The trade:** ZeRO-3/FSDP scales memory linearly with $N$ but adds an AllGather+ReduceScatter per layer — use it when you can't fit otherwise; ZeRO-1/2 give most of the memory win at DP-level comm cost.

### 2. Operational Rules
* **Rule 1 (Stage by need):** ZeRO-2 first (big memory win, DP-level comm); escalate to ZeRO-3/FSDP only when params still don't fit.
* **Rule 2 (Overlap gather with compute):** FSDP should AllGather the next layer while computing the current — else comm serializes behind compute.
* **Rule 3 (Shard size ≈ layer):** shard at the layer granularity so a gather is one layer's params, not the whole model.
* **Rule 4 (Mixed precision cuts the base):** combine with bf16 weights (and fp32 master) — the stage savings multiply.
* **Rule 5 (CPU/NVMe offload is the last resort):** ZeRO-Infinity offloads to CPU/NVMe; huge memory but slow — use only to barely fit, never for throughput.
* **Rule 6 (FSDP + TP are alternatives, often):** FSDP shards across the DP group; if you also use TP, scope them to disjoint GPU groups to avoid comm blow-up.

### 3. Reference Implementation (Python — per-stage memory estimator)
```python
def training_state_bytes(params: float, stage: int, n_gpu: int, bytes_per_param: int = 16) -> float:
    """Estimate per-GPU training-state bytes for ZeRO stage 0..3 (fp16 + fp32 Adam)."""
    total = params * bytes_per_param                       # ~16 B/param unsharded (ZeRO-0)
    if stage == 0: return total
    optim = params * 8                                     # Adam m,v (fp32)
    grad  = params * 4                                     # grads (fp32)
    param = params * (bytes_per_param - 12)               # fp16 w + fp32 master
    if stage >= 1: optim /= n_gpu
    if stage >= 2: grad  /= n_gpu
    if stage >= 3: param /= n_gpu
    return optim + grad + param

def fsdp_comm_per_step(params: float, n_layers: int, bytes_per_param: int = 2) -> float:
    """ZeRO-3/FSDP AllGathers every layer's params each fwd+bwd (Rule 3)."""
    per_layer = params * bytes_per_param / n_layers
    return per_layer * n_layers * 3                        # fwd gather + bwd gather + reduce-scatter ~

if __name__ == "__main__":
    P = 70e9
    for s in (0, 1, 2, 3):
        mem = training_state_bytes(P, stage=s, n_gpu=8)
        print(f"70B ZeRO-{s} per-GPU (8 GPU): {mem/2**30:6.1f} GiB")
```

### 4. Agent Execution Directives
* **When the model's optimizer state OOMs:** apply ZeRO-2; only if params themselves OOM go to ZeRO-3/FSDP (Rule 1).
* **When using FSDP:** verify the AllGather is overlapped with compute, else throughput collapses (Rule 2).
* **When offloading:** justify it as a fit-of-last-resort, not a throughput choice (Rule 5).
