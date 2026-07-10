---
name: ai-mixture-of-experts
description: Mixture-of-Experts (MoE) — router/top-k gating, load-balancing auxiliary loss, expert capacity, expert parallelism, and the all-to-all token dispatch. Use when designing sparse MoE models or scaling parameters without scaling FLOPs. NOT dense models — use ai-tensor-parallelism.
version: 1.0.0
---

# Skill: Mixture-of-Experts (MoE)
## System Reference: Sparse Routing + Load Balancing + Expert Parallelism (RFC-Style Engineering Spec)

### 1. Core Model
An **MoE layer** replaces one dense feed-forward with $E$ parallel **experts**; a **router** sends each token to its top-$k$ experts (usually $k=1$ or $2$). Only the chosen experts compute, so **parameters scale without scaling FLOPs** — a 1T-param MoE can cost the same compute per token as a 70B dense model.

**Routing.** $G(x) = \text{Top}_k(\text{softmax}(W_g x))$ picks the top-$k$ experts per token; their outputs are weighted by the gate's probabilities. Tokens are dispatched to their experts (an **All-to-All** under expert parallelism).

**Load balancing.** Routers collapse without intervention: a few "winning" experts attract all tokens and the rest never train. Fix with an **auxiliary loss** that pushes each expert's share of tokens toward $1/E$:
$$\mathcal{L}_{aux} = N \sum_{i=1}^{E} f_i \cdot P_i$$
where $f_i$ is the fraction of tokens routed to expert $i$ and $P_i$ is the average router probability for expert $i$. Minimizing $\mathcal{L}_{aux}$ makes $f_i \approx P_i \approx 1/E$.

**Expert capacity.** To bound memory, each expert has a capacity $C$ (tokens); overflow tokens are **dropped** (capacity-drop). Set $C \approx (\text{tokens}/E)\cdot(1+\epsilon)$; too small drops tokens (lost signal), too large wastes memory.

**Expert parallelism (EP).** Place each expert on a different GPU; tokens are **All-to-All'd** to the owning expert's GPU, computed, and All-to-All'd back. Combined with DP/TP/PP into the full $DP\cdot TP\cdot PP\cdot EP = N$ config.

### 2. Operational Rules
* **Rule 1 (Always balance the router):** add the auxiliary load-balancing loss; an unbalanced router kills experts and caps quality.
* **Rule 2 (Capacity frames the trade-off):** capacity factor $\epsilon$ trades dropped tokens for memory; dropped tokens are silent accuracy loss — monitor the drop rate.
* **Rule 3 (All-to-All is the comm cost):** EP's All-to-All is the dominant collective; size expert groups to match the interconnect.
* **Rule 4 (Finer experts, shared attention):** MoE-ify the FFN, not the attention; share attention across all experts (standard design — Switch/DeepSeek).
* **Rule 5 (Router is a single point):** a tiny router decides everything; keep it low-rank/stable and jitter-free (DeepSeek-V3 adds shared experts + bias-free routing for stability).
* **Rule 6 (Auxiliary loss weight is tiny):** $\alpha \approx 0.01$; too large distorts the main loss, too small doesn't balance.

### 3. Reference Implementation (Python — top-k routing + load-balance loss)
```python
import numpy as np

def route(gates_logits: np.ndarray, top_k: int):
    """Return (expert_indices, gate_weights) per token."""
    probs = np.exp(gates_logits - gates_logits.max(axis=-1, keepdims=True))
    probs /= probs.sum(axis=-1, keepdims=True)
    top = np.argsort(-probs, axis=-1)[:, :top_k]                     # top-k experts per token
    w = np.take_along_axis(probs, top, axis=-1)
    return top, w

def auxiliary_loss(gates_logits: np.ndarray, top_k: int) -> float:
    """Switch/DeepSeek load-balancing loss (Rule 1): f_i * P_i summed over experts."""
    probs = np.exp(gates_logits - gates_logits.max(axis=-1, keepdims=True))
    probs /= probs.sum(axis=-1, keepdims=True)                      # P_i = mean router prob
    # f_i = fraction of tokens whose argmax picked expert i (Top-1 case shown)
    argmax = probs.argmax(axis=-1)
    E = gates_logits.shape[-1]
    f = np.bincount(argmax, minlength=E) / argmax.size
    P = probs.mean(axis=0)
    return float(E * np.sum(f * P))

def token_drop_rate(tokens: int, E: int, capacity_factor: float = 1.25) -> float:
    capacity = int(tokens / E * capacity_factor)                     # Rule 2
    # if routing were uniform, overflow is rare; imbalance raises it
    return max(0.0, 1 - (E * capacity) / tokens) if capacity_factor < 1 else 0.0

if __name__ == "__main__":
    np.random.seed(0)
    logits = np.random.randn(1024, 8) * 2                            # 1024 tokens, 8 experts
    print("aux loss (should be pushed toward ~1):", round(auxiliary_loss(logits, 2), 3))
```

### 4. Agent Execution Directives
* **When designing an MoE:** wire the aux loss from day one and monitor token-drop rate (Rules 1–2).
* **When scaling:** put experts on EP GPUs; quantify the All-to-All volume against the interconnect (Rule 3).
* **When quality is off:** suspect router collapse — check the per-expert token distribution, not just the loss curve.
