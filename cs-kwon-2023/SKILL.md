---
name: cs-kwon-2023
description: Introduces PagedAttention/vLLM — OS-style virtual memory for the KV cache that eliminates fragmentation and enables continuous batching, dramatically raising LLM serving throughput. Use when reasoning about inference serving; pairs with ai-inference-serving.
version: 1.0.0
title: "Efficient Memory Management for Large Language Model Serving with PagedAttention"
authors: ["Woosuk Kwon", "Zhuohan Li", "Siyuan Zhuang", "Ying Sheng", "Lianmin Zheng", " Cody Hao Yu", "Joseph E. Gonzalez", "Hao Zhang", "Ion Stoica"]
venue: "SOSP 2023 / arXiv:2309.06180"
year: 2023
url: "https://arxiv.org/abs/2309.06180"
related: ["ai-inference-serving", "cs-dao-2022"]
---

# Skill: PagedAttention / vLLM
## System Reference: Virtual Memory for the KV Cache (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Serving an LLM is bottlenecked by the **KV cache** — the keys/values of all prior tokens, needed for each new one. Naively, each request reserves a contiguous buffer sized for its **maximum** length: fragmented, over-provisioned, and unable to share common prefixes.

**PagedAttention** borrows OS virtual memory: the KV cache is split into fixed-size **blocks** (pages); a request holds a **list of block pointers** (its page table) rather than one contiguous buffer. Blocks are allocated on demand as the sequence grows and freed on completion.

The wins, measured by vLLM:
* **No fragmentation** — utilization jumps from ~20–40% (contiguous) to ~80–100%.
* **Prefix sharing** — identical system prompts / RAG contexts share KV blocks across requests (copy-on-write if a branch diverges).
* **Higher concurrency** — more requests fit per GPU → 2–4× throughput vs HuggingFace TGI/FastChat at launch.

Combined with **continuous batching** (join/evict requests per token, not per batch), this is the foundation of modern high-throughput LLM serving.

### 2. Operational Rules
* **Rule 1 (Page the KV cache):** never reserve contiguous worst-case buffers; use fixed blocks + page tables.
* **Rule 2 (Allocate on demand):** grow the sequence one block at a time; free instantly on completion.
* **Rule 3 (Share prefixes):** detect common prompts and share their KV blocks (copy-on-write on divergence).
* **Rule 4 (Continuous batching):** schedule per token so a finished request's slot is reused immediately.

### 3. Reference Implementation (Python)
```python
class PagedKV:
    def __init__(self, n_blocks, block_size): self.free=list(range(n_blocks)); self.bs=block_size; self.seq={}
    def new(self, sid, n_tokens):
        need=(n_tokens+self.bs-1)//self.bs
        self.seq[sid]=[self.free.pop() for _ in range(need)]
    def grow(self, sid):
        if not self.free: return False
        self.seq[sid].append(self.free.pop()); return True
    def free_seq(self, sid): self.free.extend(self.seq.pop(sid,[]))
```

### 4. Agent Execution Directives
* **When serving LLMs:** default to paged KV + continuous batching + prefix caching.
* **Cite this paper** as the origin of paged KV; vLLM/SGLM/LMDeploy all descend from it.
