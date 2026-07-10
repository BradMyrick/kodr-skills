---
name: cs-bahdanau-2014
description: Adds learned alignment between decoder states and encoder hidden states (additive attention), removing the fixed-length sequence bottleneck in neural machine translation. Use when building seq2seq attention, alignment models, or tracing the lineage to self-attention.
version: 1.0.0
title: "Neural Machine Translation by Jointly Learning to Align and Translate"
authors: ["Dzmitry Bahdanau", "Kyunghyun Cho", "Yoshua Bengio"]
venue: "ICLR 2015"
year: 2014
url: "https://arxiv.org/abs/1409.0473"
related: ["cs-vaswani-2017"]
---

# Skill: Additive Attention for Sequence-to-Sequence Models
## System Reference: Encoder–Decoder with Soft Alignment (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Earlier seq2seq compressed the whole source sentence into a single fixed-length vector — a bottleneck that degrades sharply on long inputs. Bahdanau attention lets the decoder **dynamically focus** on different encoder states at each output step.

**Encoder:** a bidirectional RNN reads the source and emits annotations $h_j = [\overrightarrow{h_j};\,\overleftarrow{h_j}]$ for each source position $j$.

**Alignment scores** (additive / "concat" attention) between decoder state $s_{i-1}$ and encoder state $h_j$:
$$e_{ij} = v_a^\top \tanh(W_a\, s_{i-1} + U_a\, h_j)$$

**Attention weights** (softmax over source positions):
$$\alpha_{ij} = \frac{\exp(e_{ij})}{\sum_{k=1}^{T_x} \exp(e_{ik})}$$

**Context vector** (weighted sum of encoder annotations):
$$c_i = \sum_{j=1}^{T_x} \alpha_{ij}\, h_j$$

The decoder RNN conditions on $(c_i, s_{i-1})$ to produce the next state and output, so each target word attends to the **relevant** source words instead of one squashed vector. This is the direct ancestor of self-attention (`cs-vaswani-2017`), which replaces the RNN scan with parallel scaled dot-product attention.

### 2. Operational Rules
* **Rule 1 (Soft, differentiable alignment):** $\alpha$ is a softmax — fully differentiable and trainable end-to-end with the rest of the model.
* **Rule 2 (Per-step context):** recompute the context $c_i$ at every decoder step; never reuse a single global vector.
* **Rule 3 (Score function is swappable):** additive ($v^\top\tanh(Ws+Uh)$) is the original; dot-product/general are common alternatives — the softmax-weighted sum is the invariant.
* **Rule 4 (Mask padding):** exclude padded source positions from the softmax to avoid attending to zeros.

### 3. Reference Implementation (Python, NumPy)
```python
import numpy as np

def softmax(x, axis=-1):
    e = np.exp(x - x.max(axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)

class AdditiveAttention:
    """Bahdanau additive attention: score(s, h) = v^T tanh(W s + U h)."""
    def __init__(self, d_dec, d_enc, d_attn):
        self.W = np.random.randn(d_attn, d_dec) * 0.1
        self.U = np.random.randn(d_attn, d_enc) * 0.1
        self.v = np.random.randn(d_attn) * 0.1

    def context(self, s_prev, H, mask=None):
        # s_prev: (d_dec,)   H: (T, d_enc)
        proj = np.tanh(self.W @ s_prev[:, None] + self.U @ H.T)   # (d_attn, T)
        e = self.v @ proj                                         # (T,)        Rule 3
        if mask is not None:
            e = np.where(mask, e, -1e9)                           # Rule 4: mask padding
        alpha = softmax(e)                                        # (T,)        Rule 1
        c = alpha @ H                                             # context     Rule 2
        return c, alpha
```

### 4. Agent Execution Prompting Directives
* **When long inputs degrade:** switch from a single encoder vector to per-step attention (Rule 2) — it is the whole point of the paper.
* **When visualizing alignment:** plot the $\alpha_{ij}$ matrix; a well-trained NMT model shows a near-diagonal, mostly monotonic attention.
* **When modernizing:** Vaswani's scaled dot-product attention is the drop-in successor; note that Bahdanau's RNN scan is exactly what Transformers remove.
