---
name: ai-inference-serving
description: High-throughput LLM inference — PagedAttention/vLLM, continuous batching, KV-cache management, speculative decoding, and disaggregated prefill/decode. Use when serving LLMs or sizing inference throughput/latency. NOT training.
version: 1.0.0
---

# Skill: LLM Inference Serving
## System Reference: PagedAttention + Continuous Batching + Spec Decode (RFC-Style Engineering Spec)

### 1. Core Model
LLM inference is **memory-bandwidth bound**, and its binding cost is the **KV cache**: each generated token needs the keys/values of all prior tokens. Naively, each request reserves a contiguous buffer for its worst-case length — **fragmented, wasteful, and throughput-killing**.

**PagedAttention (vLLM).** Borrowing OS virtual memory, the KV cache is split into fixed-size **blocks** (pages); each sequence's KV is a list of block pointers. Blocks are allocated on demand and freed on completion, eliminating fragmentation and enabling **sharing** of prompt prefixes across requests (prefix caching). This often **2–4× throughput** immediately.

**Continuous (iteration-level) batching.** Classic batching waits for the longest request in a batch (head-of-line blocking). Continuous batching joins/evicts requests **per token**: as soon as one request finishes, a queued one takes its slot. Keeps the batch full and GPU-saturated.

**Prefill vs Decode asymmetry.** **Prefill** (processing the prompt) is compute-heavy (one big matmul); **Decode** (one token at a time) is memory-bandwidth-bound (small batch, tiny matmul). **Disaggregated serving** runs them on separate GPU pools tuned for each phase, raising utilization.

**Speculative decoding.** A tiny **draft** model proposes $k$ tokens; the big model verifies them in **one parallel forward**; accepted tokens are free (verified at draft cost). Trades a little compute for large latency wins when the draft is accurate. Variants: **Medusa** heads, **Eagle**, **n-gram** (free).

### 2. Operational Rules
* **Rule 1 (Page the KV cache):** use block-based KV (PagedAttention); never reserve contiguous worst-case buffers.
* **Rule 2 (Batch continuously):** join/evict per token, not per batch; keep the GPU saturated.
* **Rule 3 (Share prefixes):** cache common system prompts/RAG context across requests.
* **Rule 4 (Disaggregate prefill/decode):** run them on pools sized for their compute/memory profiles.
* **Rule 5 (Speculate when latency-bound):** add a draft model when tokens/sec matters more than peak throughput.
* **Rule 6 (Quantize for bandwidth):** serving is bandwidth-bound — int8/int4/fp8 weights multiply tokens/s per GPU at small accuracy cost.
* **Rule 7 (Size the KV cache):** $\text{KV bytes} \approx 2 \cdot L \cdot h \cdot (\text{tokens}) \cdot b$ — it grows with concurrency × context; it's usually the OOM, not the weights.

### 3. Reference Implementation (Python — paged KV cache + continuous-batching slots)
```python
from dataclasses import dataclass, field

@dataclass
class PagedKVCache:
    """OS-style paged KV cache: fixed blocks, per-sequence block lists (Rule 1)."""
    block_size: int = 16
    free: list[int] = field(default_factory=list)        # free block ids
    sequences: dict[int, list[int]] = field(default_factory=dict)  # seq -> block ids

    def allocate(self, seq_id: int, n_tokens: int):
        blocks = (n_tokens + self.block_size - 1) // self.block_size
        ids = [self.free.pop() for _ in range(blocks)]
        self.sequences[seq_id] = ids

    def extend(self, seq_id: int):
        if not self.free: return False                    # backpressure: no free block
        self.sequences[seq_id].append(self.free.pop()); return True

    def free_seq(self, seq_id: int):
        self.free.extend(self.sequences.pop(seq_id, []))  # Rule 2: free on completion

def kv_bytes(params_hidden: int, layers: int, tokens: int, bytes_each: int = 2) -> float:
    """Rule 7: KV cache bytes ~ 2 (K&V) * layers * hidden * tokens."""
    return 2 * layers * params_hidden * tokens * bytes_each

if __name__ == "__main__":
    cache = PagedKVCache(block_size=16)
    cache.free = list(range(1000))
    cache.allocate(1, 40); cache.allocate(2, 100)
    while cache.extend(1): pass                            # grow seq 1 until no free block
    cache.free_seq(2)                                      # evict finished seq -> frees blocks
    # KV for 8k context, 80 layers, hidden 8192, bf16, one request:
    print("8k ctx KV bytes:", round(kv_bytes(8192, 80, 8192)/1e9, 2), "GB")
```

### 4. Agent Execution Directives
* **When serving:** default to paged KV + continuous batching + prefix caching (Rules 1–3); quantify concurrency from the KV-cache size (Rule 7).
* **When latency-bound:** add speculative decoding (Rule 5); when throughput-bound, raise batch size and quantize (Rule 6).
* **For prefill-heavy (long prompts) or decode-heavy (long outputs):** disaggregate the two phases onto tuned pools (Rule 4).
