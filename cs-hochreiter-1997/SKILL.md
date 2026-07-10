---
name: cs-hochreiter-1997
description: Solves the vanishing/exploding gradient problem in recurrent nets with gated memory cells (LSTM) that carry error across long lags. Use when building RNNs, sequence models, or debugging long-range gradient flow.
version: 1.0.0
title: "Long Short-Term Memory"
authors: ["Sepp Hochreiter", "Jürgen Schmidhuber"]
venue: "Neural Computation, 9(8)"
year: 1997
url: "https://doi.org/10.1162/neco.1997.9.8.1735"
related: ["cs-rumelhart-1986", "cs-vaswani-2017"]
---

# Skill: Long Short-Term Memory (LSTM)
## System Reference: Gated Recurrent Memory Cell (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Plain RNNs unfold into a deep network over time, so the gradient $\partial L/\partial h_0$ is a product of many Jacobians — it **vanishes** ($\to 0$) or **explodes** ($\to \infty$) over long lags (`cs-rumelhart-1986`'s chain rule run amok). The LSTM fixes this with a **memory cell** $c_t$ whose recurrent path is nearly linear, regulated by **gates** (input $i_t$, forget $f_t$, output $o_t$; the forget gate was added by Gers et al. 2000):

$$\tilde{c}_t = \tanh(W_c x_t + U_c h_{t-1} + b_c)$$
$$i_t = \sigma(W_i x_t + U_i h_{t-1} + b_i), \quad f_t = \sigma(W_f x_t + U_f h_{t-1} + b_f), \quad o_t = \sigma(W_o x_t + U_o h_{t-1} + b_o)$$
$$c_t = f_t \odot c_{t-1} + i_t \odot \tilde{c}_t$$
$$h_t = o_t \odot \tanh(c_t)$$

where $\sigma$ is the logistic sigmoid and $\odot$ the elementwise product.

**Why gradients survive.** Differentiating the cell update gives a recurrence $\partial c_t/\partial c_{t-1} \approx f_t + (\text{gated terms})$. With the forget gate near $1$, the recurrent derivative stays near $1$, so the product over many steps neither vanishes nor explodes — the cell can store information for hundreds of steps.

### 2. Operational Rules
* **Rule 1 (Additive cell path):** the cell update is additive, not purely multiplicative — this is what preserves long-range gradients.
* **Rule 2 (Gates are multiplicative controllers):** gates in $(0,1)$ gate information flow; initialize the forget-gate bias high ($\approx 1$) so cells remember early in training.
* **Rule 3 (Gradient clipping):** LSTMs reduce but do not eliminate exploding gradients — clip the global norm.
* **Rule 4 (Refinements optional):** peephole connections and stacked (multi-layer) LSTMs are common refinements, not requirements.

### 3. Reference Implementation (Python, NumPy)
```python
import numpy as np

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

class LSTMCell:
    def __init__(self, d_x, d_h):
        s = 1.0 / np.sqrt(d_h)
        self.Wf = np.random.randn(d_h, d_x) * s; self.Uf = np.random.randn(d_h, d_h) * s
        self.Wi = np.random.randn(d_h, d_x) * s; self.Ui = np.random.randn(d_h, d_h) * s
        self.Wc = np.random.randn(d_h, d_x) * s; self.Uc = np.random.randn(d_h, d_h) * s
        self.Wo = np.random.randn(d_h, d_x) * s; self.Uo = np.random.randn(d_h, d_h) * s
        self.bf = np.ones(d_h)            # Rule 2: high forget bias
        self.bi = np.zeros(d_h); self.bc = np.zeros(d_h); self.bo = np.zeros(d_h)

    def step(self, x, h_prev, c_prev):
        f = sigmoid(self.Wf @ x + self.Uf @ h_prev + self.bf)
        i = sigmoid(self.Wi @ x + self.Ui @ h_prev + self.bi)
        o = sigmoid(self.Wo @ x + self.Uo @ h_prev + self.bo)
        c_tilde = np.tanh(self.Wc @ x + self.Uc @ h_prev + self.bc)
        c = f * c_prev + i * c_tilde      # Rule 1: additive update
        h = o * np.tanh(c)
        return h, c
```

### 4. Agent Execution Prompting Directives
* **When gradients still vanish:** check forget-gate bias initialization (Rule 2) and sequence length; use gradient clipping for explosions.
* **When choosing architecture:** LSTMs excel at long, variable-length sequences, but Transformers (`cs-vaswani-2017`) usually win when data is abundant and fully parallel.
* **When debugging shapes:** all gates share the hidden dimension $d_h$; input / forget / output / candidate each carry their own $(W, U, b)$.
