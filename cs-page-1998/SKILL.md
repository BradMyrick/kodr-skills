---
name: cs-page-1998
description: Ranks web pages via the stationary distribution of a damped random walk (PageRank power iteration). Use when implementing link-analysis ranking, graph centrality, or Markov-chain stationary vectors.
version: 1.0.0
title: "The PageRank Citation Ranking: Bringing Order to the Web"
authors: ["Lawrence Page", "Sergey Brin", "Rajeev Motwani", "Terry Winograd"]
venue: "Stanford InfoLab Technical Report 1999-66"
year: 1998
url: "http://ilpubs.stanford.edu:8090/422/"
---

# Skill: PageRank & the Random Surfer
## System Reference: Damped Random-Walk Ranking (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
PageRank models a **random surfer** who, on a graph of $N$ pages, at each step either follows a random out-link (probability $d \approx 0.85$, the *damping factor*) or teleports to a uniformly random page (probability $1-d$). PageRank is the **stationary distribution** of this Markov chain.

Let $C(T) = \text{outdegree}(T)$ and $\mathrm{in}(A)$ the set of pages linking into $A$. The rank of $A$ (normalized so ranks sum to $1$):

$$PR(A) = \frac{1-d}{N} + d \sum_{T \in \mathrm{in}(A)} \frac{PR(T)}{C(T)}$$

**Matrix form.** Let $M$ be the column-stochastic transition matrix of the raw link graph ($M_{ij} = 1/C(j)$ if $j \to i$). The **Google matrix** blends it with uniform teleportation:

$$G = d\,M + \frac{1-d}{N}\,\mathbf{1}\mathbf{1}^{\top}$$

PageRank is the principal eigenvector satisfying $G\,\pi = \pi$ (eigenvalue $1$). Because every column is strictly positive, $G$ is primitive and the stationary vector is unique — computed by **power iteration**:

$$\pi_{k+1} = G\,\pi_k, \qquad \pi_k \to \pi$$

### 2. Operational Rules
* **Rule 1 (Conservation):** ranks always sum to $1$; renormalize after every iteration to absorb floating-point drift.
* **Rule 2 (Dangling nodes):** a page with no out-links leaks probability mass; redistribute its rank uniformly across all $N$ pages before the next step.
* **Rule 3 (Convergence):** iterate until $\lVert \pi_{k+1} - \pi_k \rVert_1 < \varepsilon$; on the web graph this takes roughly $\log N / (1-d)$ iterations.
* **Rule 4 (Teleport guarantees uniqueness):** with $d < 1$ the chain is ergodic; with $d = 1$ periodic/reducible graphs (rank sinks, cycles) break convergence.

### 3. Reference Implementation (Python)
```python
import numpy as np

def pagerank(adj: np.ndarray, d: float = 0.85,
             tol: float = 1e-8, max_iter: int = 1000) -> np.ndarray:
    """adj[i,j] = 1 if page j links to page i. Returns rank vector summing to 1."""
    n = adj.shape[0]
    outdeg = adj.sum(axis=0)                       # C(j) per column
    # column-stochastic M; handle dangling (zero-outdegree) columns
    dangling = outdeg == 0
    M = np.zeros((n, n))
    nonzero = outdeg > 0
    M[:, nonzero] = adj[:, nonzero] / outdeg[nonzero]

    pr = np.full(n, 1.0 / n)
    teleport = np.full(n, 1.0 / n)
    for _ in range(max_iter):
        # Rule 2: redistribute dangling mass uniformly
        dangling_mass = pr[dangling].sum() / n
        new_pr = (1 - d) * teleport + d * (M @ pr) + d * dangling_mass   # Rule 1 follows below
        new_pr /= new_pr.sum()                       # Rule 1: renormalize
        if np.abs(new_pr - pr).sum() < tol:          # Rule 3: L1 convergence
            return new_pr
        pr = new_pr
    return pr
```

### 4. Agent Execution Prompting Directives
* **When ranking a graph:** always build the *column-stochastic* matrix and confirm it has no all-zero columns unhandled — dangling nodes are the #1 numerical bug.
* **When the result diverges:** check that $d < 1$ and that mass is conserved each step (sum to 1); a rank sink means teleport is missing.
* **When scaling to billions of pages:** note power iteration is matrix-free over sparse adjacency — never materialize $G$.
