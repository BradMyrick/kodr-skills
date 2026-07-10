---
name: ai-collective-comms
description: Collective communication primitives — AllReduce (ring/tree), AllGather, ReduceScatter, Broadcast — over NCCL, with bandwidth/roofline analysis and comm-compute overlap. Use when quantifying or optimizing the communication cost of distributed training. Quantify before proposing any parallelism.
version: 1.0.0
---

# Skill: Collective Communication & the Roofline
## System Reference: NCCL Collectives + Ring Algorithms + Bandwidth Math (RFC-Style Engineering Spec)

### 1. Core Model
Distributed training is bottlenecked by **collective communication** as much as by FLOPs. Knowing each primitive's **data volume** and **bandwidth characteristic** is how you predict and fix throughput.

**The primitives** (on GPU clusters, implemented by **NCCL** over NVLink/InfiniBand):
* **Broadcast:** one rank → all. Volume $V$.
* **Reduce:** all → one (summed). Volume $V$ to one rank.
* **AllReduce:** all → all (each gets the sum). *The workhorse of data-parallel grad sync.*
* **AllGather:** each contributes a piece, all receive the concatenation.
* **ReduceScatter:** each gets a reduced slice of the result.

**Ring AllReduce** (bandwidth-optimal): split the buffer into $N$ chunks; each node sends/receives one chunk per step around a ring. Total data moved per node:
$$\text{per-node volume} = \frac{2(N-1)}{N}\,V \;\approx\; 2V \quad (\text{independent of }N)$$
So AllReduce **scales**: doubling nodes doesn't double per-node traffic. Ring latency is $2(N-1)$ steps — for latency-sensitive small collectives, **tree** algorithms (fewer steps, more bandwidth) win.

**The roofline.** Time for a collective ≈ latency + volume/bandwidth. The **arithmetic intensity** (FLOPs/byte) tells you if a layer is compute- or comm-bound:
$$\text{comm-bound when} \quad \frac{\text{FLOPs}}{\text{bytes comm}} < \frac{\text{peak FLOP/s}}{\text{peak bytes/s}}$$
Always compute this ratio before claiming a parallelism scheme is "efficient."

**Overlap.** Modern training overlaps the AllReduce for layer $i$ with the backward compute of layer $i+1$ (gradient bucketing + async streams). Un-overlapped, the collective serializes behind compute and throughput halves.

### 2. Operational Rules
* **Rule 1 (Quantify the volume):** for every proposed scheme, sum the collective bytes/step and divide by link bandwidth — that's your comm floor.
* **Rule 2 (Ring for large, tree for small):** large AllReduces are bandwidth-bound → ring; tiny ones are latency-bound → tree/recursive-doubling.
* **Rule 3 (Overlap comm with compute):** launch collectives on the gradient as soon as it's ready; never block the whole backward then AllReduce.
* **Rule 4 (Bucket to amortize latency):** fuse small tensors into one collective near the bandwidth×latency product.
* **Rule 5 (Topology-aware ranks):** map ranks so the ring/tree follows NVLink intra-node then InfiniBand across nodes; a bad rank mapping can halve effective bandwidth.
* **Rule 6 (NCCL is the floor):** profile with Nsight/nccl-tests; theoretical bandwidth is rarely achieved — measure the fraction.

### 3. Reference Implementation (Python — ring AllReduce volume + roofline)
```python
def ring_allreduce_volume_per_node(buffer_bytes: int, n: int) -> float:
    """Per-node bytes moved in a ring AllReduce (Rule 2): ~2V, independent of n."""
    return 2 * (n - 1) / n * buffer_bytes

def collective_time(volume_bytes: float, bandwidth_bytes_s: float, latency_s: float, n_steps: int) -> float:
    return latency_s * n_steps + volume_bytes / bandwidth_bytes_s

def is_comm_bound(flops: float, bytes_comm: float, peak_flops_s: float, peak_bytes_s: float) -> bool:
    """Roofline: comm-bound when arithmetic intensity < machine balance (Rule 1)."""
    balance = peak_flops_s / peak_bytes_s            # FLOPs per byte at the ridge
    return (flops / bytes_comm) < balance

if __name__ == "__main__":
    V = 70e9 * 2                                      # 70B params grads in fp16
    for n in (8, 64, 512):
        print(f"ring AllReduce per-node (n={n:3d}): {ring_allreduce_volume_per_node(V,n)/1e12:.1f} TB")
    # A100: ~312 TFLOP/s bf16, ~600 GB/s NVLink -> balance ~520 FLOP/byte
    print("comm-bound?", is_comm_bound(flops=1e12, bytes_comm=1e9,
                                        peak_flops_s=312e12, peak_bytes_s=600e9))
```

### 4. Agent Execution Directives
* **Before recommending any parallelism:** compute the collective volume/step and the roofline ratio; cite the bandwidth number (Rule 1).
* **For grad sync:** use ring AllReduce for large models; verify comm overlaps backward (Rule 3).
* **When throughput is low:** profile NCCL (nccl-tests) and check the rank-to-topology mapping before blaming the model (Rules 5–6).
