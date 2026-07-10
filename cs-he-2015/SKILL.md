---
name: cs-he-2015
description: Enables training of very deep networks via residual (skip) connections that learn identity-referenced functions, solving the degradation problem. Use when building deep CNNs, ResNets, or reasoning about gradient flow through depth.
version: 1.0.0
title: "Deep Residual Learning for Image Recognition"
authors: ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"]
venue: "CVPR 2016"
year: 2015
url: "https://arxiv.org/abs/1512.03385"
related: ["cs-krizhevsky-2012", "cs-rumelhart-1986"]
---

# Skill: Residual Networks (ResNet) & Identity Skip Connections
## System Reference: Identity-Mapped Residual Blocks (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Adding layers should never hurt — a deeper model can always emulate a shallower one by learning the identity for the extra layers. Yet in practice **deeper nets train worse** (the *degradation problem*): plain networks incur higher training error as depth grows, even without overfitting. ResNets fix this by having each block learn a **residual**.

Instead of stacking layers to fit an underlying mapping $\mathcal{H}(x)$ directly, let them fit the residual:
$$\mathcal{F}(x) := \mathcal{H}(x) - x \quad\Longrightarrow\quad \mathcal{H}(x) = \mathcal{F}(x) + x$$
If the optimal mapping is the identity, driving $\mathcal{F}(x) \to 0$ is easy (shrink weights) — far simpler than learning an identity through a stack of nonlinear layers.

**Forward** of a residual block:
$$y = \mathcal{F}(x, \{W_i\}) + x$$
where $\mathcal{F}$ is typically two or three conv + ReLU layers and $+x$ is a **skip (shortcut) connection**. When channel/spatial dims differ, $x$ is projected by a $1\times1$ conv: $y = \mathcal{F}(x) + W_s x$.

**Gradient flow.** During backprop:
$$\frac{\partial \mathcal{L}}{\partial x} = \frac{\partial \mathcal{L}}{\partial y}\left(1 + \frac{\partial \mathcal{F}}{\partial x}\right)$$
The additive $1$ lets gradient flow directly to earlier layers regardless of $\partial\mathcal{F}/\partial x$, so signal neither vanishes nor decays — enabling 152+ layer networks (vs AlexNet's 8).

### 2. Operational Rules
* **Rule 1 (Identity shortcut is the default):** use a plain identity $+x$ whenever dims match; project only on channel/stride change ($1\times1$ conv).
* **Rule 2 (Residual, not the whole map):** the block computes $\mathcal{F}(x)$ then adds $x$ — don't add a second nonlinearity on the shortcut path (pre-activation variants exist but change dynamics).
* **Rule 3 (Addition after the block):** the elementwise add happens after $\mathcal{F}$, before the final activation; respect the ordering.
* **Rule 4 (Depth is now cheap):** stacking blocks (ResNet-50/101/152) monotonically improves error; bottleneck blocks ($1\times1\!-\!3\times3\!-\!1\times1$) control cost.

### 3. Reference Implementation (Python, PyTorch-style)
```python
import torch.nn as nn

def conv3x3(in_c, out_c, stride=1):
    return nn.Conv2d(in_c, out_c, 3, stride=stride, padding=1, bias=False)

class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, in_c, out_c, stride=1):
        super().__init__()
        self.conv1 = conv3x3(in_c, out_c, stride); self.bn1 = nn.BatchNorm2d(out_c)
        self.conv2 = conv3x3(out_c, out_c);        self.bn2 = nn.BatchNorm2d(out_c)
        self.relu = nn.ReLU(inplace=True)
        # Rule 1: project only when shape changes
        self.shortcut = (nn.Sequential(
            nn.Conv2d(in_c, out_c, 1, stride=stride, bias=False), nn.BatchNorm2d(out_c))
            if stride != 1 or in_c != out_c else nn.Identity())

    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + self.shortcut(x)      # Rule 3: residual add after F(x)
        return self.relu(out)

class ResNet(nn.Module):
    def __init__(self, layers, num_classes=1000):
        super().__init__()
        self.inplanes = 64
        self.stem = nn.Sequential(
            nn.Conv2d(3, 64, 7, stride=2, padding=3, bias=False), nn.BatchNorm2d(64),
            nn.ReLU(inplace=True), nn.MaxPool2d(3, stride=2, padding=1))
        self.layer1 = self._make_layer(64,  layers[0], stride=1)
        self.layer2 = self._make_layer(128, layers[1], stride=2)
        self.layer3 = self._make_layer(256, layers[2], stride=2)
        self.layer4 = self._make_layer(512, layers[3], stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(512 * BasicBlock.expansion, num_classes)

    def _make_layer(self, planes, n, stride):
        layers = [BasicBlock(self.inplanes, planes, stride)] + [BasicBlock(planes, planes) for _ in range(n - 1)]
        self.inplanes = planes * BasicBlock.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.stem(x)
        for lyr in (self.layer1, self.layer2, self.layer3, self.layer4):
            x = lyr(x)
        return self.fc(self.avgpool(x).flatten(1))
```

### 4. Agent Execution Prompting Directives
* **When a deep net won't train:** add residual skips before reaching for tricks — the degradation problem is almost always the culprit past ~30 layers.
* **When dims change (stride/channel):** remember to project the shortcut (Rule 1); a mismatched add silently corrupts gradients.
* **When citing depth:** ResNet-152 (3.57% top-5 ImageNet error, 2015) is the headline result; it swept ILSVRC/COCO that year.
