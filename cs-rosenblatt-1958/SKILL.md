---
name: cs-rosenblatt-1958
description: Implements the perceptron, a binary linear classifier trained by error-correction (the perceptron learning rule). Use when building linear classifiers, teaching the convergence theorem, or contrasting with Minsky's limitations.
version: 1.0.0
title: "The Perceptron: A Probabilistic Model for Information Storage and Organization in the Brain"
authors: ["Frank Rosenblatt"]
venue: "Psychological Review, 65(6)"
year: 1958
url: "https://doi.org/10.1037/h0042519"
related: ["cs-rumelhart-1986"]
---

# Skill: The Perceptron & Error-Correction Learning
## System Reference: Sensory–Association–Response (S–A–R) Network (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
The perceptron is the first *learnable* neural model: a sensory layer projects inputs onto association units, which feed a binary **linear threshold unit** (the response unit). For an input vector $x \in \mathbb{R}^n$, weights $w$, and bias $b$:

$$z = w \cdot x + b = \sum_{i=1}^{n} w_i x_i + b, \qquad \hat{y} = \begin{cases} 1 & z \ge 0 \\ 0 & z < 0 \end{cases}$$

The **perceptron learning rule** updates weights only when the prediction is wrong (error-correction), with learning rate $\eta > 0$ and true label $y \in \{0,1\}$:

$$\Delta w_i = \eta\,(y - \hat{y})\,x_i, \qquad \Delta b = \eta\,(y - \hat{y})$$

**Convergence Theorem (Novikoff, 1953/1962).** If the training set is linearly separable with geometric margin $\gamma > 0$ and all inputs satisfy $\|x\| \le R$, then the perceptron makes at most

$$\left(\frac{R}{\gamma}\right)^2$$

mistakes before converging to a separating hyperplane — regardless of input order. If the data is *not* separable, the weights oscillate forever — the single-layer ceiling that motivated multi-layer networks.

### 2. Operational Rules
* **Rule 1 (Linear boundary):** the decision surface is a single hyperplane; nonlinear predicates (XOR, parity, connectedness) are unreachable.
* **Rule 2 (Update on error only):** if $\hat{y} = y$, leave the weights unchanged.
* **Rule 3 (Sign of update):** a false negative ($\hat{y}=0, y=1$) *adds* $\eta x$; a false positive ($\hat{y}=1, y=0$) *subtracts* $\eta x$ — always pushing $w$ toward the misclassified point's correct side.
* **Rule 4 (Separability gate):** before claiming convergence, verify separability; otherwise switch to a loss-based method (logistic / multi-layer).

### 3. Reference Implementation (Python)
```python
import numpy as np

class Perceptron:
    def __init__(self, n_features: int, lr: float = 1.0, max_epochs: int = 1000):
        self.w = np.zeros(n_features)
        self.b = 0.0
        self.lr = lr
        self.max_epochs = max_epochs

    def predict_one(self, x: np.ndarray) -> int:
        return 1 if (np.dot(self.w, x) + self.b) >= 0 else 0

    def fit(self, X: np.ndarray, y: np.ndarray) -> int:
        """Returns the number of updates (mistakes) until convergence."""
        updates = 0
        for _ in range(self.max_epochs):
            errors = 0
            for xi, yi in zip(X, y):
                y_hat = self.predict_one(xi)
                err = yi - y_hat            # Rule 2: nonzero only on misclassification
                if err != 0:
                    self.w += self.lr * err * xi   # Rule 3
                    self.b += self.lr * err
                    updates += 1
                    errors += 1
            if errors == 0:                 # converged (separable within budget)
                break
        return updates
```

### 4. Agent Execution Prompting Directives
* **When teaching the model:** always pair the rule with Novikoff's bound so the separability assumption is explicit.
* **When a perceptron fails to converge:** diagnose non-separability first (plot XOR) rather than tuning $\eta$ — bigger learning rates cannot fix a hyperplane that cannot exist.
* **When extending:** frame multi-layer/backpropagation (`cs-rumelhart-1986`) as the direct remedy to the single-hyperplane ceiling.
