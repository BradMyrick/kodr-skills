---
name: cs-brown-2020
description: Generates text from a 175B-parameter autoregressive language model conditioned by in-context few-shot examples (GPT-3). Use when designing few-shot prompts, autoregressive LMs, or reasoning about in-context learning and scaling laws.
version: 1.0.0
title: "Language Models are Few-Shot Learners"
authors: ["Tom B. Brown", "Benjamin Mann", "Nick Ryder", "et al. (31 authors, OpenAI)"]
venue: "NeurIPS 2020"
year: 2020
url: "https://arxiv.org/abs/2005.14165"
related: ["cs-vaswani-2017"]
---

# Skill: Language Models are Few-Shot Learners (GPT-3)
## System Reference: Massive Autoregressive Transformer + In-Context Learning (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
GPT-3 is a **decoder-only autoregressive Transformer** language model (`cs-vaswani-2017`) scaled to 175B parameters (96 layers, $d_{\text{model}}=12288$, 96 heads, context window 2048), trained on ~300B filtered tokens (Common Crawl, WebText2, Books1, Books2, Wikipedia).

**Autoregressive factorization.** The probability of a token sequence $x_{1:T}$ decomposes left-to-right:

$$P(x_{1:T}) = \prod_{t=1}^{T} P(x_t \mid x_{<t};\, \theta)$$

The model is trained to **minimize the negative log-likelihood** (next-token cross-entropy):

$$\mathcal{L}(\theta) = -\sum_{t=1}^{T} \log P(x_t \mid x_{<t};\, \theta)$$

**In-context learning — the core claim.** At inference, no parameters are updated. Instead the model is *conditioned* on a natural-language prompt. Three regimes of increasing conditioning:

$$P(\text{output} \mid \underbrace{\text{task description}}_{\text{zero-shot}},\; \underbrace{(x_i, y_i)_{i=1}^{k}}_{\text{few-shot examples}},\; \text{query})$$

* **Zero-shot:** prompt is the task instruction alone.
* **One-shot:** + a single demonstration.
* **Few-shot:** + $k$ demonstrations (typically $k \le 64$).

**Scaling law (Kaplan et al., 2020, referenced).** Test loss decays as a power law in parameters $N$, data $D$, and compute $C$:

$$\mathcal{L}(N) \propto N^{-\alpha}, \quad \alpha \approx 0.076$$

— so few-shot competence *emerges* from scale, not architectural novelty or gradient updates.

### 2. Operational Rules
* **Rule 1 (No gradient updates at inference):** few-shot learning means conditioning only — distinguish it sharply from fine-tuning.
* **Rule 2 (Format is the API):** the arrangement of demonstrations, delimiters, and instructions *is* the program; consistent formatting across examples dominates almost any other lever.
* **Rule 3 (Left-to-right only):** no bidirectional attention; structure prompts so all needed context precedes the query.
* **Rule 4 (Context budget):** demonstrations compete for the 2048-token window; prefer few high-quality examples over many.
* **Rule 5 (Calibration):** GPT-3 is poorly calibrated and sensitive to phrasing — always report results over prompt paraphrases.

### 3. Reference Implementation (Python, pseudo-torch)
```python
import torch
import torch.nn.functional as F

def lm_loss(logits, targets):
    """Standard next-token cross-entropy. logits: (T, V), targets: (T,) of ints."""
    return F.cross_entropy(logits, targets)

@torch.no_grad()
def generate(model, ids, max_new_tokens, temperature=1.0):
    """Greedy/temperature-sampled autoregressive decoding."""
    for _ in range(max_new_tokens):
        logits = model(ids[:, -context_window:])      # Rule 3: feed trailing window
        next_logits = logits[:, -1, :] / temperature
        probs = torch.softmax(next_logits, dim=-1)
        ids = torch.cat([ids, torch.multinomial(probs, 1)], dim=1)  # left-to-right append
    return ids

def few_shot_prompt(task: str, examples: list[tuple[str, str]], query: str) -> str:
    """Assemble an in-context prompt. Formatting consistency = Rule 2."""
    parts = [f"Task: {task}\n"]
    for q, a in examples:                              # zero/one/few-shot regimes
        parts.append(f"Q: {q}\nA: {a}\n")
    parts.append(f"Q: {query}\nA:")                    # model continues here
    return "".join(parts)

# prompt = few_shot_prompt("Translate English to French",
#                          [("hello","bonjour"), ("water","eau")], "fire")
```

### 4. Agent Execution Prompting Directives
* **When few-shot underperforms:** fix formatting/delimiters first (Rule 2); only then vary example count and order.
* **When a task "needs training":** verify it truly exceeds in-context capability — many tasks improve with clearer instructions rather than fine-tuning.
* **When reasoning about limits:** flag calibration, hallucination, and the 2048-token ceiling explicitly; these are the documented GPT-3 failure modes.
* **When citing:** attribute in-context *learning* to scale (this paper) and the architecture to `cs-vaswani-2017`; keep the two claims distinct.
