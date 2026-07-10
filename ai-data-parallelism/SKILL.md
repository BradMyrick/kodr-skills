---
name: ai-data-parallelism
description: Data parallelism — DP, DistributedDataParallel (DDP), gradient bucketing, the parameter-server architecture, and async/decentralized/gossip SGD with staleness. Use when scaling training by replicating the model across GPUs. NOT for sharding the model itself — use ai-zero-fsdp.
version: 1.0.0
---

# Skill: Data Parallelism (DP / DDP / Parameter Server)
## System Reference: Replicated Model + Gradient Synchronization (RFC-Style Engineering Spec)

### 1. Core Model
In **data parallelism** every GPU holds a **full copy of the model**; the global batch is split into per-GPU mini-batches. Each GPU computes a forward/backward pass producing **local gradients**; the gradients are **averaged** (AllReduce) and applied identically everywhere, so all replicas stay in sync.

**Synchronous SGD (DDP).** The classic form: after backward, AllReduce-mean the gradients across all ranks, then each rank steps the optimizer. Deterministic, converges like a single large batch. **Gradient bucketing** (DDP) fuses many small gradient tensors into one large AllReduce to amortize latency.

**Ring AllReduce.** The bandwidth-optimal collective for averaging: each node sends/receives $\frac{2(N-1)}{N}$ of the gradient volume — the per-node bandwidth is **independent of N** (scales). See `ai-collective-comms`.

**Parameter Server (PS).** An alternative topology: workers pull params, compute grads, **push** grads to servers; servers aggregate and apply. Decouples aggregation from workers but the server can be a bottleneck and adds **staleness** (async updates). Largely superseded by AllReduce/FSDP for dense training.

**Asynchronous / decentralized SGD.** Workers update without a global barrier: **async SGD** applies stale gradients (bounded staleness $s$); **decentralized/gossip SGD** averages with neighbors only, trading exact averaging for no global collective. Higher throughput, subtler convergence.

### 2. Operational Rules
* **Rule 1 (Sync SGD averages, then steps):** AllReduce-mean the gradients, then each rank runs the optimizer — never step on local-only gradients.
* **Rule 2 (Bucket gradients):** fuse small tensors into large AllReduces to keep the interconnect saturated; tune the bucket cap to the bandwidth-latency product.
* **Rule 3 (Overlap comm with compute):** launch the AllReduce for layer $i$ as soon as its gradient is ready, while later layers keep computing backward (`ai-collective-comms`).
* **Rule 4 (Bound staleness in async):** tolerate staleness $s$ only where the convergence theory holds; pure async can diverge on sharp losses.
* **Rule 5 (DP needs the model to fit on one GPU):** if a single replica doesn't fit, you're past DP — move to ZeRO/FSDP/TP/PP.
* **Rule 6 (Identical seeds + order):** for reproducibility, fix seeds and gradient accumulation order; floating-point AllReduce is not associative, so order affects results at the ULP level.

### 3. Reference Implementation (Python — synchronous data-parallel step)
```python
import numpy as np

def allreduce_mean(grads_per_rank: list[np.ndarray]) -> np.ndarray:
    """Simulates the ring AllReduce that averages gradients across ranks (Rule 1)."""
    stacked = np.stack(grads_per_rank, axis=0)
    return stacked.mean(axis=0)

def data_parallel_step(replica_grads: list[np.ndarray], params: np.ndarray, lr: float) -> np.ndarray:
    """Each rank computed grads; average them, then step identically everywhere."""
    avg = allreduce_mean(replica_grads)                  # Rule 1: collective average
    return params - lr * avg                             # identical update on every rank

def gradient_bucketing_demo(layer_grads: list[np.ndarray], bucket_cap: int) -> list[np.ndarray]:
    """Fuse small grads into <=bucket_cap tensors before AllReduce (Rule 2)."""
    buckets, current, used = [], [], 0
    for g in layer_grads:
        if used + g.nbytes > bucket_cap and current:
            buckets.append(np.concatenate([x.ravel() for x in current])); current, used = [], 0
        current.append(g); used += g.nbytes
    if current: buckets.append(np.concatenate([x.ravel() for x in current]))
    return buckets

if __name__ == "__main__":
    p = np.ones(4)
    g = [np.array([1.0, 2, 3, 4]), np.array([3.0, 4, 5, 6])]   # two ranks' grads
    p2 = data_parallel_step(g, p, lr=0.1)
    print("updated params:", p2)                              # averaged grad = [2,3,4,5]
```

### 4. Agent Execution Directives
* **When scaling a model that fits per-GPU:** use DDP with bucketing + comm/compute overlap; verify the AllReduce isn't serialized behind backward.
* **When the model no longer fits per replica:** switch to ZeRO/FSDP (`ai-zero-fsdp`), not more DP.
* **When considering async/gossip:** quantify the staleness and confirm the loss landscape tolerates it before trading exactness for throughput.
