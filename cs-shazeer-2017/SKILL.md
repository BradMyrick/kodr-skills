---
name: cs-shazeer-2017
description: Introduces the sparsely-gated Mixture-of-Experts layer — a learned router selects top-k experts per token, scaling parameters without scaling FLOPs. Use when reasoning about MoE routing and load balancing; pairs with ai-mixture-of-experts.
version: 1.0.0
title: "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer"
authors: ["Noam Shazeer", "Azalia Mirhoseini", "Krzysztof Maziarz", "Andy Davis", "Quoc V. Le", "Geoffrey E. Hinton", "Jeff Dean"]
venue: "ICLR 2017 / arXiv:1701.06538"
year: 2017
url: "https://arxiv.org/abs/1701.06538"
related: ["ai-mixture-of-experts", "cs-shoeybi-2019"]
---

# Skill: Sparsely-Gated Mixture-of-Experts
## System Reference: Top-k Router + Load-Balancing Loss (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Replace one dense FFN with $E$ experts; a **gating network** $G(x) = \text{softmax}(W_g x)$ routes each token to its top-$k$ experts (here $k=1$ with noisy top-k for exploration). Only chosen experts compute, so parameters grow with $E$ while **FLOPs per token stay roughly constant** — the foundation of trillion-parameter sparse models.

$$G(x) = \text{Top}_k\big(\text{softmax}(W_g x)\big), \qquad y = \sum_{i \in \text{Top}_k} G(x)_i \, E_i(x)$$

**The load-balancing loss** prevents router collapse (a few experts hoarding all tokens). Define:
* $f_i$ = fraction of tokens routed to expert $i$,
* $P_i$ = average router probability for expert $i$,

$$\mathcal{L}_{\text{bal}} = N \sum_{i=1}^{E} f_i \cdot P_i$$

Minimized when $f_i = P_i = 1/E$ (uniform). The product form matters: penalizing $f_i$ alone lets the router keep high $P_i$ on a popular expert and game the metric.

The paper trained a 137B-parameter model on translation at the FLOP budget of a far smaller dense model.

### 2. Operational Rules
* **Rule 1 (Always balance):** ship the auxiliary loss; an unbalanced router starves experts and caps quality.
* **Rule 2 (Small weight):** $\alpha \approx 10^{-2}$ on $\mathcal{L}_{\text{bal}}$; large distorts the task loss.
* **Rule 3 (Capacity bounds memory):** set per-expert capacity and drop overflow tokens; monitor the drop rate.

### 3. Reference Implementation (Python)
```python
import numpy as np
def route(gates_logits, top_k):
    p = np.exp(gates_logits - gates_logits.max(-1, keepdims=True)); p /= p.sum(-1, keepdims=True)
    idx = np.argsort(-p, -1)[:, :top_k]
    w = np.take_along_axis(p, idx, -1)
    return idx, w
def balance_loss(gates_logits):
    p = np.exp(gates_logits - gates_logits.max(-1, keepdims=True)); p /= p.sum(-1, keepdims=True)
    E = gates_logits.shape[-1]
    f = np.bincount(p.argmax(-1), minlength=E) / p.shape[0]
    return float(E * np.sum(f * p.mean(0)))
```

### 4. Agent Execution Directives
* **When designing MoE:** reproduce the $f_i \cdot P_i$ balance loss (not $f_i$ alone) and watch token-drop rate.
* **Cite this paper** as the MoE routing + balancing origin; DeepSeek/Switch are direct descendants.
