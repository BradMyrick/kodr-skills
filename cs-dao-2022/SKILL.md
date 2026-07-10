---
name: cs-dao-2022
description: Introduces FlashAttention — an IO-aware exact attention algorithm that fuses the attention computation to minimize HBM reads/writes, enabling long context without approximation. Use when reasoning about attention memory/IO or long-context training; pairs with ai-parallelism-overview.
version: 1.0.0
title: "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness"
authors: ["Tri Dao", "Daniel Y. Fu", "Stefano Ermon", "Atri Rudra", "Christopher Ré"]
venue: "NeurIPS 2022 / arXiv:2205.14135"
year: 2022
url: "https://arxiv.org/abs/2205.14135"
related: ["ai-parallelism-overview", "cs-vaswani-2017"]
---

# Skill: FlashAttention — IO-Aware Exact Attention
## System Reference: Tiling + Kernel Fusion for HBM-Bandwidth Efficiency (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Standard attention (`cs-vaswani-2017`) materializes the $N \times N$ attention matrix in HBM: $S = QK^\top$, $P = \text{softmax}(S)$, $O = PV$. For long sequences this is **$O(N^2)$ HBM writes/reads** — bandwidth-bound and memory-bloated.

FlashAttention computes the **same** result (exact, not approximate) but **fuses** the whole computation into one kernel that never materializes the full $N\times N$ matrix. It **tiles** $Q,K,V$ into blocks that fit in SRAM, and uses the **online-softmax** trick to compute a running max and stable normalization incrementally:

$$m_i^{(j)} = \max\big(m_i^{(j-1)},\; \text{rowmax}(S_{ij})\big), \quad
\ell_i^{(j)} = e^{m_i^{(j-1)}-m_i^{(j)}}\ell_i^{(j-1)} + \text{rowsum}(e^{S_{ij}-m_i^{(j)}})$$

This yields **exact** attention with $O(N)$ HBM traffic (vs $O(N^2)$) and $O(N)$ activation memory — a 2–4× speedup and the unlock for multi-thousand-token (later million-token) context.

### 2. Operational Rules
* **Rule 1 (It's exact):** FlashAttention is not an approximation — outputs match standard attention within fp error.
* **Rule 2 (Fuse to cut HBM traffic):** the win is IO (HBM reads/writes), not FLOPs; profile HBM, not arithmetic.
* **Rule 3 (Block-size tuning):** tile size trades SRAM occupancy for parallelism; tune per architecture.
* **Rule 4 (Enable for long context):** the asymptotic gain grows with sequence length; short sequences see little benefit.

### 3. Reference Implementation (Python — online-softmax block)
```python
import numpy as np
def flash_attention(Q, K, V, block=64):
    """Exact attention via online softmax + tiling (illustrative, not GPU-fused)."""
    N = Q.shape[0]; d = Q.shape[1] / np.sqrt(Q.shape[1])
    O = np.zeros_like(V); m = np.full((N,), -np.inf); l = np.zeros((N,))
    for j in range(0, N, block):
        Sj = (Q @ K[j:j+block].T) / np.sqrt(Q.shape[1])          # block of scores
        mj = Sj.max(-1)
        mj_new = np.maximum(m, mj)
        a = np.exp(m - mj_new)[:, None]
        b = np.exp(Sj - mj_new[:, None])
        l = a[:, 0] * l + b.sum(-1)
        O = a * O + b @ V[j:j+block]
        m = mj_new
    return O / l[:, None]
```

### 4. Agent Execution Directives
* **For any long-context model:** enable FlashAttention; it's exact and faster — there's no reason not to.
* **Cite this paper** as the IO-aware fusion origin; FlashAttention-2/3 extend it to async/low-precision.
