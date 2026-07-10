---
name: ai-pipeline-parallelism
description: Pipeline parallelism — GPipe vs 1F1B vs interleaved schedules, the pipeline bubble, and micro-batch scheduling. Use when partitioning a model's layers across GPUs (stages). Prefer ai-tensor-parallelism intra-node; use pipeline across nodes.
version: 1.0.0
---

# Skill: Pipeline Parallelism
## System Reference: Layer-Stages + Micro-batches + Bubble Minimization (RFC-Style Engineering Spec)

### 1. Core Model
**Pipeline parallelism (PP)** splits a model's **layers** into $p$ consecutive **stages**, each on a GPU. A micro-batch flows stage→stage; to keep all stages busy you chop the global batch into $m$ **micro-batches** and pipeline them.

The cost of pipelining is the **bubble**: the time stages sit idle while the first/last micro-batches fill and drain the pipe.

**Schedules:**
* **GPipe (all-forward/all-backward):** run all $m$ micro-batches forward, then all backward. Bubble fraction:
$$\text{bubble} = \frac{p-1}{m}$$
Big $m$ shrinks the bubble but needs memory for $m$ in-flight activations.
* **1F1B (one-forward-one-backward):** once the pipe is full, alternate one forward and one backward pass; **activation memory is bounded to $p$ micro-batches** (not $m$) — the production default.
* **Interleaved 1F1B:** each stage owns $v$ non-contiguous chunks of layers; with $v$ virtual stages the bubble shrinks further:
$$\text{bubble} = \frac{1}{v}\cdot\frac{p-1}{m}$$
at the cost of more comm hops. Megatron-LM uses this for large clusters.

### 2. Operational Rules
* **Rule 1 (PP goes across nodes):** PP's inter-stage comm is one activation per micro-batch — cheap enough for slow inter-node links; keep TP intra-node.
* **Rule 2 (Bound the bubble):** $m \gg p$ for GPipe; prefer 1F1B to bound memory while shrinking the bubble.
* **Rule 3 (Balance the stages):** pipeline throughput = slowest stage; split layers so each stage has equal FLOPs/memory.
* **Rule 4 (Interleave for more GPUs):** with interleaved 1F1B ($v>1$) you halve the bubble per $v$, but add comm hops — tune for the topology.
* **Rule 5 (Activation memory matters):** GPipe holds $m$ micro-batches of activations; 1F1B holds ~$p$ — prefer 1F1B when memory-bound.

### 3. Reference Implementation (Python — bubble math + 1F1B schedule)
```python
def gpipe_bubble(p: int, m: int) -> float:
    """GPipe bubble fraction = (p-1)/m (Rule 2)."""
    return (p - 1) / m

def interleaved_bubble(p: int, m: int, v: int) -> float:
    """Interleaved-1F1B bubble = (1/v) * (p-1)/m (Rule 4)."""
    return (1 / v) * (p - 1) / m

def one_f1b_schedule(p: int, m: int) -> list[str]:
    """Generate a 1F1B device-time schedule; each entry is 'F' or 'B' per stage slot."""
    # Steady state: once stage i has (p - i) forwards in flight, it alternates F/B.
    schedule = []
    for stage in range(p):
        warmup = p - 1 - stage                    # forwards before the first backward can run
        row = ["F"] * min(warmup, m)
        remaining = m - len(row)
        row += ["FB"] * remaining                 # steady-state one-forward-one-backward
        schedule.append(row)
    return schedule

if __name__ == "__main__":
    p, m = 4, 16
    print(f"GPipe bubble (p={p},m={m}): {gpipe_bubble(p,m)*100:.1f}%")
    print(f"1F1B  bubble (p={p},m={m},v=1): {interleaved_bubble(p,m,1)*100:.1f}%")
    print(f"interleaved (v=4):             {interleaved_bubble(p,m,4)*100:.1f}%")
    sched = one_f1b_schedule(p, m)
    for i, row in enumerate(sched): print(f" stage {i}: {row[:8]}...")
```

### 4. Agent Execution Directives
* **When partitioning across nodes:** use PP across nodes + TP within nodes; verify stage FLOPs are balanced (Rule 3).
* **When picking a schedule:** default to 1F1B (memory-bounded bubble); reach for interleaved 1F1B on large clusters to halve the bubble.
* **Always report the bubble fraction:** it's the headline PP cost; quote $(p-1)/m$ (or $/v$) for the chosen config.
