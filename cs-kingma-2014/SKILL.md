---
name: cs-kingma-2014
description: Optimizes stochastic objectives with adaptive estimates of first and second moments plus bias correction (Adam). Use when selecting or configuring optimizers, tuning learning rates, or debugging optimizer behavior.
version: 1.0.0
title: "Adam: A Method for Stochastic Optimization"
authors: ["Diederik P. Kingma", "Jimmy Ba"]
venue: "ICLR 2015"
year: 2014
url: "https://arxiv.org/abs/1412.6980"
related: ["cs-rumelhart-1986"]
---

# Skill: Adam — Adaptive Moment Estimation
## System Reference: First/Second-Moment Optimizer with Bias Correction (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Adam fuses **momentum** (an exponential moving average of the gradient) with **RMSProp** (an EMA of squared gradients) and corrects the startup bias that otherwise drives estimates toward zero early in training.

Per parameter $\theta$, at step $t$ with gradient $g_t$:

**First moment (mean):**
$$m_t = \beta_1 m_{t-1} + (1-\beta_1)\, g_t$$
**Second moment (uncentered variance):**
$$v_t = \beta_2 v_{t-1} + (1-\beta_2)\, g_t^2$$
**Bias correction** (since $m, v$ start at $0$ and are biased low initially):
$$\hat{m}_t = \frac{m_t}{1-\beta_1^t}, \qquad \hat{v}_t = \frac{v_t}{1-\beta_2^t}$$
**Update:**
$$\theta_t = \theta_{t-1} - \eta \,\frac{\hat{m}_t}{\sqrt{\hat{v}_t} + \varepsilon}$$

**Defaults:** $\beta_1 = 0.9,\; \beta_2 = 0.999,\; \varepsilon = 10^{-8},\; \eta \approx 10^{-3}$.

**Key properties.** The step size is roughly $\eta$ (the ratio $\hat m/\sqrt{\hat v}\approx \pm1$); the update is **invariant to gradient rescaling** (scale cancels in the ratio); and bias correction makes early steps effective immediately. The paper proves a $O(1/\sqrt t)$ regret bound on convex objectives.

### 2. Operational Rules
* **Rule 1 (Bias correction is mandatory):** never drop $\hat m, \hat v$ early in training — without it the first steps are grossly undersized.
* **Rule 2 (ε placement):** use $\hat m_t / (\sqrt{\hat v_t} + \varepsilon)$; some frameworks use $\hat m_t / \sqrt{\hat v_t + \varepsilon}$, which differs numerically at small $\hat v$.
* **Rule 3 (Defaults travel):** start with $\beta_1{=}0.9,\ \beta_2{=}0.999,\ \varepsilon{=}10^{-8}$; tune $\eta$ first, decay it late.
* **Rule 4 (Weight decay ≠ L2):** decoupled weight decay (AdamW) is the correct way to add $\ell_2$ regularization; naive L2 inside Adam under-regularizes large-weight parameters.
* **Rule 5 (Watch non-convergence):** Adam is the de-facto optimizer for deep nets despite no non-convex guarantee; on some convex problems use AMSGrad to restore convergence.

### 3. Reference Implementation (Python)
```python
import numpy as np

class Adam:
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8):
        self.lr, (self.b1, self.b2), self.eps = lr, betas, eps
        self.m = [np.zeros_like(p) for p in params]   # first moment
        self.v = [np.zeros_like(p) for p in params]   # second moment
        self.t = 0

    def step(self, params, grads):
        self.t += 1
        for i, (p, g) in enumerate(zip(params, grads)):
            self.m[i] = self.b1 * self.m[i] + (1 - self.b1) * g            # first moment
            self.v[i] = self.b2 * self.v[i] + (1 - self.b2) * (g * g)      # second moment
            m_hat = self.m[i] / (1 - self.b1 ** self.t)                    # Rule 1: bias-correct
            v_hat = self.v[i] / (1 - self.b2 ** self.t)
            p -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)             # Rule 2: ε outside sqrt
```

### 4. Agent Execution Prompting Directives
* **When training diverges:** lower $\eta$ first; verify bias correction is on (Rule 1) and that weight decay uses AdamW (Rule 4).
* **When comparing to SGD:** Adam converges faster and needs less tuning; SGD+momentum can still win on large-scale vision with careful schedules.
* **When generalization is poor:** suspect AdamW-vs-Adam-L2 misuse or too-high $\eta$; consider switching to SGD for the final epochs.
