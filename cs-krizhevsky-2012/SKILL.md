---
name: cs-krizhevsky-2012
description: Classifies images with a deep 8-layer convolutional network (AlexNet) using ReLU activations, dropout, and GPU training. Use when building CNN image classifiers, porting AlexNet-style architectures, or applying ReLU/dropout.
version: 1.0.0
title: "ImageNet Classification with Deep Convolutional Neural Networks"
authors: ["Alex Krizhevsky", "Ilya Sutskever", "Geoffrey E. Hinton"]
venue: "NeurIPS (NIPS) 2012"
year: 2012
url: "https://papers.nips.cc/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html"
related: ["cs-rumelhart-1986", "cs-he-2015"]
---

# Skill: Deep Convolutional Image Classification (AlexNet)
## System Reference: 8-Layer ReLU CNN on GPU (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
AlexNet established that depth + the right nonlinearities decisively beats hand-tuned features on ImageNet (1000-way, 1.2M images). The network has **8 learned layers**: 5 convolutional + 3 fully-connected (~60M parameters).

**Per-neuron forward pass** (convolutional and dense layers alike):

$$z = w \cdot x + b, \qquad a = f(z)$$

**ReLU nonlinearity** — the key training-speed breakthrough, replacing saturating $\tanh$:

$$f(z) = \max(0, z), \qquad f'(z) = \begin{cases}1 & z > 0 \\ 0 & z \le 0\end{cases}$$

**Softmax** over the 1000 logits and the **multinomial cross-entropy** loss (here for the true class $c$):

$$p_i = \frac{e^{z_i}}{\sum_j e^{z_j}}, \qquad \mathcal{L} = -\log p_c = -z_c + \log\sum_j e^{z_j}$$

**Dropout** (applied to the first two FC layers, keep rate $1-p$, $p=0.5$): at train time multiply activations by a Bernoulli mask $m \sim \text{Bernoulli}(1-p)$ and scale by $1/(1-p)$; at test time use the full (unmasked) network.

**Local response normalization** across adjacent feature maps and **overlapping max-pooling** ($3\times3$, stride 2) complete the regularization/feature recipe.

### 2. Operational Rules
* **Rule 1 (ReLU over saturating activations):** prefer ReLU for feed-forward image nets — it converges ~6× faster than $\tanh$ at equal depth.
* **Rule 2 (Dropout is train-only):** apply the mask and scaling only during training; inference uses the full weights.
* **Rule 3 (Augment before training):** random $224\times224$ crops, horizontal flips, and PCA color jitter are part of the model's effective capacity, not an afterthought.
* **Rule 4 (Optimizer):** SGD with momentum $0.9$, weight decay $5\!\times\!10^{-4}$, batch $128$, initial LR $0.01$ reduced $10\times$ when validation plateaus — the canonical deep-image training recipe.
* **Rule 5 (Depth feeds gradients):** the vanishing-gradient caveat of `cs-rumelhart-1986` is mitigated here by ReLU + pooling short-circuits; respect both when designing very deep nets.

### 3. Reference Implementation (Python, PyTorch-style)
```python
import torch
import torch.nn as nn

class AlexNet(nn.Module):
    def __init__(self, num_classes: int = 1000):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3,   96,  kernel_size=11, stride=4), nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(96,  256, kernel_size=5, padding=2), nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(256, 384, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(384, 384, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.5), nn.Linear(256 * 6 * 6, 4096), nn.ReLU(inplace=True),
            nn.Dropout(0.5), nn.Linear(4096, 4096),         nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)        # logits; apply softmax/cross-entropy at loss time
```

### 4. Agent Execution Prompting Directives
* **When porting the architecture:** reproduce the 96→256→384→384→256 conv widths and the 4096-4096-1000 head; these are load-bearing, not arbitrary.
* **When training stalls:** verify ReLU (not $\tanh$), dropout train/test asymmetry, and LR schedule before touching depth.
* **When modernizing:** note that BatchNorm and residual connections postdate this paper — use them to go deeper than 8 layers, but cite AlexNet as the ReLU+depth origin.
