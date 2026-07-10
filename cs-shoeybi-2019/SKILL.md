---
name: cs-shoeybi-2019
description: Introduces Megatron-LM tensor parallelism — column/row weight splitting that inserts exactly one AllReduce per Transformer block. Use when reasoning about intra-layer/model parallelism for LLMs. Pairs with ai-tensor-parallelism.
version: 1.0.0
title: "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism"
authors: ["Mohammad Shoeybi", "Mostofa Patwary", "Raul Puri", "Patrick LeGresley", "Jared Casper", "Bryan Catanzaro"]
venue: "arXiv:1909.08053"
year: 2019
url: "https://arxiv.org/abs/1909.08053"
related: ["ai-tensor-parallelism", "cs-rajbhandari-2019"]
---

# Skill: Megatron-LM — Tensor-Parallel Transformers
## System Reference: Column/Row Weight Splitting with Minimal Collectives (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Megatron-LM showed how to split a Transformer's weights across GPUs with **minimal communication**: one `AllReduce` per MLP block and one per attention block.

An MLP block is $Y = \mathrm{GeLU}(X A)\,B$. Split it as:
* $A$ **column-parallel**: $A = [A_1, \dots, A_N]$, each rank holds $A_i$, computes $Y_i = \mathrm{GeLU}(X A_i)$ — a slice of output columns, **no comm**, and the nonlinearity is applied **locally** on the sharded columns.
* $B$ **row-parallel**: $B = [B_1; \dots; B_N]^\top$, each rank holds $B_i$, computes the partial $Z_i = Y_i B_i$, then **AllReduce-sums**: $Z = \sum_i Z_i$.

So the block needs exactly **one AllReduce**, placed after the nonlinearity — the cheapest possible placement. Self-attention splits the heads the same way (column-parallel $W_Q,W_K,W_V$, row-parallel output projection → one AllReduce).

This made 8–24 billion-parameter models trainable on a handful of GPUs and is the foundation of every modern 3D-parallel stack.

### 2. Operational Rules
* **Rule 1 (One AllReduce per block):** pair column-parallel input with row-parallel output so a Transformer block needs a single collective.
* **Rule 2 (Keep TP intra-node):** the per-block AllReduce demands NVLink; don't span slow inter-node links.
* **Rule 3 (Heads divide cleanly):** the attention head count must be divisible by the TP degree.

### 3. Reference Implementation (Python)
```python
import numpy as np
def megatron_mlp(X, A_shards, B_shards, gelu):
    Yi = [gelu(X @ Ai) for Ai in A_shards]      # column-parallel: nonlinearity local
    Zi = [Yi[k] @ B_shards[k] for k in range(len(B_shards))]
    out = np.zeros_like(Zi[0])
    for z in Zi: out += z                         # the single AllReduce (Rule 1)
    return out
```

### 4. Agent Execution Directives
* **When designing TP:** reproduce the column→nonlinearity→row→AllReduce placement; verify it equals the unsharded math.
* **Always pair** with ZeRO/DP for the full $DP \times TP \times PP$ config (`cs-rajbhandari-2019`, `ai-parallelism-overview`).
