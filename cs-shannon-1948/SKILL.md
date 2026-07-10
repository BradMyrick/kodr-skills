---
name: cs-shannon-1948
description: Quantifies information via entropy and mutual information and derives the Shannon-Hartley channel-capacity limit. Use when computing entropy, designing source/channel codes, or reasoning about compression and bandwidth limits.
version: 1.0.0
title: "A Mathematical Theory of Communication"
authors: ["Claude E. Shannon"]
venue: "Bell System Technical Journal, 27(3)"
year: 1948
url: "https://doi.org/10.1002/j.1538-7305.1948.tb01338.x"
related: ["cs-turing-1936"]
---

# Skill: Information Theory & Channel Capacity
## System Reference: The Mathematical Communication Model (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
A communication system is: **source → transmitter → (noisy) channel → receiver → destination**. Two theorems bound the whole field.

**Information entropy** of a discrete source with symbol distribution $p(x)$:

$$H(X) = -\sum_{x} p(x) \log_2 p(x) \quad \text{[bits/symbol]}$$

Entropy measures the average surprise: the minimum expected code length needed to losslessly describe the source.

**Mutual information** between input $X$ and output $Y$:

$$I(X;Y) = H(X) - H(X|Y) = \sum_{x,y} p(x,y) \log_2 \frac{p(x,y)}{p(x)\,p(y)}$$

**Channel capacity** is the maximum rate at which information can traverse a channel reliably:

$$C = \max_{p(X)} I(X;Y) \quad \text{[bits/use]}$$

**Shannon–Hartley theorem** — a bandlimited continuous channel of bandwidth $W$ (Hz), signal power $S$, and additive noise power $N$:

$$C = W \log_2\!\left(1 + \frac{S}{N}\right) \quad \text{[bits/sec]}$$

* **Source-coding theorem (noiseless):** a source can be compressed to an average of $H(X)$ bits/symbol and no fewer; prefix codes (e.g. Huffman) approach this bound.
* **Channel-coding theorem (noisy):** for any rate $R < C$ there exist codes making the error probability arbitrarily small; for $R > C$ reliable communication is impossible.

### 2. Operational Rules
* **Rule 1 (Log base):** use $\log_2$ for bits; multiply $\ln$-based results by $1/\ln 2$ to convert.
* **Rule 2 (Convention $0\log 0 = 0$):** guard zero-probability symbols before taking logarithms.
* **Rule 3 (Capacity is a max):** capacity is found by optimizing over the *input* distribution, not read off a single $p(X)$.
* **Rule 4 (Surprise principle):** improbable events carry more information ($-\log p$); uniform sources maximize entropy for a fixed alphabet.

### 3. Reference Implementation (Python)
```python
import numpy as np

def entropy(p: np.ndarray) -> float:
    """Shannon entropy in bits. p is a probability vector summing to 1."""
    p = np.asarray(p, dtype=np.float64)
    p = p[p > 0]                       # Rule 2: drop zero-probability symbols
    return float(-(p * np.log2(p)).sum())

def mutual_information(px: np.ndarray, Pxy: np.ndarray) -> float:
    """I(X;Y). px: marginal over X. Pxy[i,j] = P(X=i, Y=j)."""
    py = Pxy.sum(axis=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(Pxy > 0, Pxy / (px[:, None] * py[None, :]), 0.0)
    return float((Pxy * np.log2(ratio)).sum())

def shannon_hartley(bandwidth_hz: float, signal_w: float, noise_w: float) -> float:
    """Channel capacity in bits/sec for an AWGN bandlimited channel."""
    return bandwidth_hz * np.log2(1.0 + signal_w / noise_w)

def binary_entropy(p: float) -> float:
    """H of a Bernoulli(p) source — handy for BSC analysis."""
    if p in (0.0, 1.0):
        return 0.0
    return -p * np.log2(p) - (1 - p) * np.log2(1 - p)
```

### 4. Agent Execution Prompting Directives
* **When sizing a link:** compute $C$ first; treat any claimed rate $R > C$ as physically impossible and flag it.
* **When compressing:** report both the achieved average length and the entropy lower bound $H(X)$ so the gap is explicit.
* **When debugging a noisy channel:** tabulate $H(X)$, $H(X|Y)$, and $I(X;Y)$; capacity is the ceiling of $I$ over input distributions.
