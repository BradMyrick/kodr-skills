---
name: ai-resilience-checkpointing
description: Resilience for large-scale training — synchronous/async checkpointing, resharding across parallelism degrees, and fault tolerance at 10k+ GPUs (MTBF, redundancy, stragglers). Use when training won't survive a restart, or when checkpoint I/O dominates. NOT for inference caching.
version: 1.0.0
---

# Skill: Resilience & Checkpointing at Scale
## System Reference: Durable Snapshots + Resharding + Failure Math (RFC-Style Engineering Spec)

### 1. Core Model
At 10,000+ GPUs the mean time between **node/GPU failures** is hours, not days — a training run that can't **checkpoint and resume** cannot finish. A checkpoint must capture the full training state: model params, optimizer state (Adam m/v), LR scheduler, RNG state, data-loader position, and the parallelism layout.

**Checkpoint I/O is the hidden bottleneck.** A 1T-param model's fp16+Adam state is ~16 TB; writing it synchronously stalls every GPU for minutes. Two fixes:
* **Distributed/parallel checkpointing:** each rank writes its own shard concurrently to a shared FS/object store; the logical checkpoint is a *directory* of shards, not one file.
* **Asynchronous checkpointing:** copy the live state to CPU/a staging buffer (or use copy-on-write) and write to the FS in the background while training continues — trading a little memory for no stall.
* **In-memory replicas:** keep a recent copy on neighbor GPUs (replication factor 2) so a single failure recovers in seconds without touching the FS.

**Resharding.** You often train with one parallelism degree (e.g. TP=8) and resume/eval with another (TP=1). A good checkpoint format is **shard-agnostic**: store a logical tensor list + metadata, and the loader re-partitions across whatever $DP\cdot TP\cdot PP\cdot EP$ you resume with. Hard resharding (fixed layout) is a frequent restart failure.

**Failure math.** If per-node MTBF is $M$ hours across $N$ nodes, the cluster's MTBF is $\approx M/N$. At $N=10{,}000$ and $M=10^5$ h, that's a failure every ~10 hours — checkpoint cadence and recovery time must keep expected lost work small.

### 2. Operational Rules
* **Rule 1 (Checkpoint everything stateful):** params, optimizer, scheduler, RNG, dataloader position, layout — omitting any breaks exact resume.
* **Rule 2 (Distributed + async):** write shards in parallel, off the critical path; never serialize one giant file.
* **Rule 3 (Shard-agnostic format):** store logical tensors + metadata so you can resume under a different parallelism degree.
* **Rule 4 (Cadence beats recovery):** checkpoint often enough that expected lost work (cadence × failure rate) is acceptable; keep recent in-memory replicas for fast single-failure recovery.
* **Rule 5 (Verify before trusting):** a checkpoint you can't load is worse than none — test restore in CI, and checksum shards.
* **Rule 6 (Handle stragglers/elision):** at scale, detect and elide/skip stuck ranks or use elastic training rather than blocking the whole job.

### 3. Reference Implementation (Python — async checkpoint + MTBF)
```python
import threading, time

class AsyncCheckpointer:
    """Copy state to a staging buffer now; persist in the background (Rule 2)."""
    def __init__(self): self._writer = None; self._lock = threading.Lock()
    def save(self, state: dict, path: str):
        snapshot = {k: v.copy() if hasattr(v, "copy") else v for k, v in state.items()}  # COW-staged
        def _write():
            time.sleep(0.01)                                  # simulates FS/object-store write
            with self._lock: pass
        t = threading.Thread(target=_write, daemon=True); t.start()
        self._writer = t
        return snapshot                                       # training continues immediately

    def wait(self):
        if self._writer: self._writer.join()

def cluster_mtbf_hours(node_mtbf_h: float, n_nodes: int) -> float:
    """Expected hours between failures across the cluster (Rule 4)."""
    return node_mtbf_h / max(1, n_nodes)

def expected_lost_work_hours(cadence_h: float, n_nodes: int, node_mtbf_h: float,
                             recovery_h: float) -> float:
    """Crude model: each failure loses ~half a cadence window + recovery time."""
    rate = 1.0 / cluster_mtbf_hours(node_mtbf_h, n_nodes)     # failures/hour
    return rate * (cadence_h / 2 + recovery_h)

if __name__ == "__main__":
    print("cluster MTBF @10k nodes:", round(cluster_mtbf_hours(1e5, 10_000), 1), "h")
    print("expected lost work/day:", round(expected_lost_work_hours(0.5, 10_000, 1e5, 0.1) * 24, 2), "GPU-h/GPU-day")
```

### 4. Agent Execution Directives
* **For any long run:** wire distributed+async checkpointing with a shard-agnostic format (Rules 2–3); verify restore in CI.
* **When sizing cadence:** balance checkpoint overhead against the expected-lost-work from failures (Rule 4).
* **At extreme scale:** add in-memory replicas for sub-minute single-failure recovery (Rule 4) and elastic/straggler handling (Rule 6).
