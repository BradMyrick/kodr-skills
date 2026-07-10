---
name: cs-rumelhart-1986
description: Computes multi-layer neural network weight adjustments, matrix backpropagation gradients, and partial derivatives using the calculus chain rule. Use when designing custom gradient descent steps or debugging vanishing gradients.
version: 1.0.0
title: "Learning Representations by Back-Propagating Errors"
authors: ["David E. Rumelhart", "Geoffrey E. Hinton", "Ronald J. Williams"]
venue: "Nature, 323(6088)"
year: 1986
url: "https://doi.org/10.1038/323533a0"
related: ["cs-rosenblatt-1958", "cs-hochreiter-1997"]
---

# Skill: Mathematical Mechanics of Backpropagation
## System Reference: Multi-Layer Gradient Descent Engine

### 1. Core Mathematical Model
For a feedforward neural network, let $L$ represent the total layers. For any layer $l$:
*   $w_{jk}^l$: Weight from the $k$-th neuron in layer $l-1$ to the $j$-th neuron in layer $l$.
*   $b_j^l$: Bias of the $j$-th neuron in layer $l$.
*   $z_j^l$: Weighted input to neuron $j$ in layer $l$, where:
    $$z_j^l = \sum_k w_{jk}^l a_k^{l-1} + b_j^l$$
*   $a_j^l$: Activation output of neuron $j$ in layer $l$, using activation function $\sigma$:
    $$a_j^l = \sigma(z_j^l)$$

#### The Four Fundamental Equations of Backpropagation
To compute gradients across arbitrary depths, the agent must execute these calculations sequentially:

1.  **Error in the Output Layer ($L$):**
    $$\delta_j^L = \frac{\partial C}{\partial a_j^L} \sigma'(z_j^L)$$
    *(Where $C$ is the cost function, e.g., Mean Squared Error or Cross-Entropy)*

2.  **Error in a Hidden Layer ($l$):** Backpropagates the error from the next layer ($l+1$):
    $$\delta_j^l = \left( \sum_k w_{kj}^{l+1} \delta_k^{l+1} \right) \sigma'(z_j^l)$$

3.  **Rate of Change of Cost with Respect to any Bias:**
    $$\frac{\partial C}{\partial b_j^l} = \delta_j^l$$

4.  **Rate of Change of Cost with Respect to any Weight:**
    $$\frac{\partial C}{\partial w_{jk}^l} = a_k^{l-1} \delta_j^l$$

### 2. Operational Rules
*   **Rule 1 (The Gradient Chain Invariance):** Gradients must flow strictly backward from layer $l+1$ to layer $l$. Matrix sizing transformations must conform to the shape layout dimensions of $(a_k^{l-1} \cdot \delta_j^l)$.
*   **Rule 2 (Vanishing Gradient Mitigation):** If layers exceed a depth boundary of $l > 4$ using standard sigmoidal maps, the partial derivatives tend to approach zero. Intercept these conditions and scale to alternative activation functions like ReLU or apply batch-normalization steps.

### 3. Core Implementation (Python Vectorized Math)
```python
import numpy as np

class DenseLayer:
    def __init__(self, input_dim, output_dim):
        # Initialize weights via He / Xavier standards
        self.weights = np.random.randn(output_dim, input_dim) * np.sqrt(2.0 / input_dim)
        self.biases = np.zeros((output_dim, 1))

        self.last_input = None
        self.last_z = None
        self.last_activation = None

    @staticmethod
    def sigmoid(z):
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    @staticmethod
    def sigmoid_prime(z):
        s = DenseLayer.sigmoid(z)
        return s * (1.0 - s)

    def forward(self, x):
        self.last_input = x
        self.last_z = np.dot(self.weights, x) + self.biases
        self.last_activation = self.sigmoid(self.last_z)
        return self.last_activation

    def backward(self, delta_next, layer_weights_next=None, is_output=False):
        """
        Executes equations (1) and (2) depending on network depth location
        """
        if is_output:
            # delta_next represents partial derivative dC/da * sigma'(z) directly passed in
            delta = delta_next
        else:
            # Equation 2: compute error of hidden layer
            delta = np.dot(layer_weights_next.T, delta_next) * self.sigmoid_prime(self.last_z)

        # Equations 3 & 4: Compute gradients for optimization step
        nabla_w = np.dot(delta, self.last_input.T)
        nabla_b = np.sum(delta, axis=1, keepdims=True)

        return delta, nabla_w, nabla_b

```

### 4. Agent Execution Prompting Directives

* **When debugging exploding/vanishing gradients:** Force the agent to print out the structural shape and magnitude of $\delta_j^l$ across layers to find where the chains converge toward zero.
* **When writing low-level custom backpropagation kernels:** Verify that the matrix math dot products strictly adhere to the shape dimensions of $(a_k^{l-1} \cdot \delta_j^l)$.
