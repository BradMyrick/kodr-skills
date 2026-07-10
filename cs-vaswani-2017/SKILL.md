---
name: cs-vaswani-2017
description: Computes sequence representations via scaled dot-product self-attention and multi-head attention without recurrence or convolution (Transformer). Use when building attention layers, transformers, or debugging attention scaling and positional encoding.
version: 1.0.0
title: "Attention Is All You Need"
authors: ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Łukasz Kaiser", "Illia Polosukhin"]
venue: "NeurIPS 2017"
year: 2017
url: "https://arxiv.org/abs/1706.03762"
related: ["cs-bahdanau-2014", "cs-brown-2020"]
---

# Skill: Attention Is All You Need (The Transformer)
## System Reference: Self-Attentive Encoder–Decoder (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
The Transformer replaces recurrence/convolution entirely with attention, allowing full parallelism over a sequence of length $n$ with $d$-dimensional embeddings.

**Scaled dot-product attention.** Given queries $Q$, keys $K$, and values $V$ (each derived from the input by learned projections), with key dimension $d_k$:

$$\mathrm{Attention}(Q, K, V) = \mathrm{softmax}\!\left(\frac{Q K^{\top}}{\sqrt{d_k}}\right) V$$

The $\sqrt{d_k}$ scaling prevents large dot products from pushing softmax into vanishing-gradient saturation.

**Multi-head attention** runs $h$ parallel attentions over projected subspaces, then concatenates and re-projects:

$$\mathrm{MultiHead}(Q,K,V) = \mathrm{Concat}(\mathrm{head}_1,\dots,\mathrm{head}_h)\, W^{O}$$
$$\mathrm{head}_i = \mathrm{Attention}(Q W_i^{Q},\; K W_i^{K},\; V W_i^{V})$$

**Positional encoding** injects order (attention itself is permutation-equivariant), using fixed sinusoids of dimension $d_{\text{model}}$:

$$PE_{(pos,\,2i)} = \sin\!\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right), \quad PE_{(pos,\,2i+1)} = \cos\!\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)$$

**Per-layer recipe:** each (encoder/decoder) layer = `[multi-head attention] → add & LayerNorm → [position-wise FFN: 2 linear layers with ReLU] → add & LayerNorm`. The decoder masks future positions so generation stays autoregressive. Base model: 6 encoder + 6 decoder layers, $d_{\text{model}}=512$, $h=8$, $d_k=d_v=64$.

### 2. Operational Rules
* **Rule 1 (Always scale by $\sqrt{d_k}$):** omitting it saturates softmax and kills gradients as $d_k$ grows.
* **Rule 2 (Causal mask in the decoder):** set attention logits to $-\infty$ above the diagonal before softmax to block looking ahead.
* **Rule 3 (Add positional info):** attention alone is order-agnostic — sinusoidal or learned PE is mandatory.
* **Rule 4 (Residuals need matching dims):** the `add` step requires the projection output dimension to equal $d_{\text{model}}$ (hence the final $W^O$).
* **Rule 5 (Complexity is $O(n^2 d)$):** the quadratic sequence cost is the dominant scaling concern; flag it for long contexts.

### 3. Reference Implementation (Python, NumPy)
```python
import numpy as np

def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def scaled_dot_product_attention(Q, K, V, mask=None):
    # Q: (..., n, d_k)  K: (..., n, d_k)  V: (..., n, d_v)
    d_k = Q.shape[-1]
    scores = Q @ K.swapaxes(-2, -1) / np.sqrt(d_k)        # Rule 1
    if mask is not None:
        scores = np.where(mask == 0, -1e9, scores)        # Rule 2 (causal/pad mask)
    weights = softmax(scores, axis=-1)
    return weights @ V

def multi_head_attention(x, Wq, Wk, Wv, Wo, n_heads):
    # x: (n, d_model); each W projects to (d_model, d_model)
    d_model = x.shape[-1]
    assert d_model % n_heads == 0
    d_k = d_model // n_heads
    Q, K, V = x @ Wq, x @ Wk, x @ Wv                      # (n, d_model)
    def split(t):                                          # -> (n_heads, n, d_k)
        return t.reshape(n, n_heads, d_k).transpose(1, 0, 2)
    heads = scaled_dot_product_attention(split(Q), split(K), split(V))  # (n_heads, n, d_k)
    concat = heads.transpose(1, 0, 2).reshape(n, d_model)  # Rule 4
    return concat @ Wo

def positional_encoding(max_len, d_model):
    pos = np.arange(max_len)[:, None]
    i   = np.arange(d_model)[None, :]
    angle = pos / np.power(10000, (2 * (i // 2)) / d_model)   # Rule 3
    pe = np.zeros((max_len, d_model))
    pe[:, 0::2] = np.sin(angle[:, 0::2])
    pe[:, 1::2] = np.cos(angle[:, 1::2])
    return pe
```

### 4. Agent Execution Prompting Directives
* **When attention NaNs out:** check the $\sqrt{d_k}$ scaling and the mask sentinel — unmasked futures or missing scaling are the usual culprits.
* **When porting to a framework:** keep Q/K/V projections separate per head; do not collapse heads before the softmax.
* **When extending to LLMs:** GPT/decoder-only models (e.g. `cs-brown-2020`) drop the encoder and rely solely on the masked multi-head self-attention block.
