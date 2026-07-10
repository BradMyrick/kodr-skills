---
name: ai-rlhf-infra
description: Infrastructure for RLHF/RLAIF — the actor/critic/reference/reward four-model setup, PPO and GRPO, the generation (rollout) loop, and the memory/communication bottlenecks. Use when building RL fine-tuning systems. NOT for the preference-data annotation pipeline.
version: 1.0.0
---

# Skill: RLHF / RLAIF Infrastructure
## System Reference: Four-Model RL Loop + PPO/GRPO (RFC-Style Engineering Spec)

### 1. Core Model
Reinforcement Learning from Human Feedback aligns a model to preferences. A single RLHF step is **expensive**: it coordinates **four models** in flight:

1. **Actor (policy)** — the model being trained; generates responses and is updated.
2. **Reference policy** — a frozen copy of the pre-aligned model; its log-probs define the KL penalty that keeps the actor from drifting too far.
3. **Reward model** — scores responses from learned human preferences (or an AI judge in RLAIF).
4. **Critic (value model)** — estimates state values to reduce PPO variance (omitted in GRPO).

**The loop:** (a) **rollout** — the actor generates responses to prompts; (b) score them with the reward model + a KL term vs the reference; (c) compute the **advantage**; (d) update the actor (and critic) with PPO. Rollout is the throughput bottleneck — it's inference at scale, interleaved with training.

**PPO objective** (clipped):
$$\mathcal{L}^{PPO} = \mathbb{E}\big[\min(r_t A_t,\; \text{clip}(r_t, 1-\epsilon, 1+\epsilon)A_t)\big], \quad r_t = \frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{old}}(a_t|s_t)}$$

**GRPO** drops the critic: sample a **group** of $G$ responses per prompt, baseline the advantage against the group's mean reward, and update the actor directly — **one fewer multi-billion-parameter model** in memory, which is why GRPO (DeepSeek) is displacing PPO for large models.

### 2. Operational Rules
* **Rule 1 (Rollout is the bottleneck):** generation is inference interleaved with training; co-locate/size the inference pool or it starves the trainers.
* **Rule 2 (Keep the KL anchor):** always penalize $\mathrm{KL}(\pi_\theta \| \pi_{ref})$; without it the policy reward-hacks into gibberish.
* **Rule 3 (Freeze reference + reward):** the reference and reward models are frozen — use inference mode, no optimizer state, to save memory.
* **Rule 4 (Prefer GRPO at scale):** dropping the critic removes a whole model from memory and comms; use PPO only when a critic is justified.
* **Rule 5 (Offload the frozen models):** reference/reward can live on cheaper/offloaded devices; only the actor (and critic) need training-grade memory.
* **Rule 6 (Watch reward hacking):** monitor the KL and response-length/entropy; a rising reward with rising KL/length is hacking, not alignment.

### 3. Reference Implementation (Python — PPO clipped objective + GRPO advantage)
```python
import numpy as np

def ppo_objective(logprob_old: np.ndarray, logprob_new: np.ndarray,
                  advantage: np.ndarray, clip_eps: float = 0.2) -> float:
    """Clipped PPO surrogate (Rule: the actor update)."""
    ratio = np.exp(logprob_new - logprob_old)
    surr1 = ratio * advantage
    surr2 = np.clip(ratio, 1 - clip_eps, 1 + clip_eps) * advantage
    return float(np.mean(np.minimum(surr1, surr2)))        # maximize

def kl_penalty(logprob_ref: np.ndarray, logprob_actor: np.ndarray, beta: float) -> float:
    """Approx KL(actor || ref) penalty keeping the policy anchored (Rule 2)."""
    return beta * float(np.mean(np.exp(logprob_actor - logprob_ref) - 1 - (logprob_actor - logprob_ref)))

def grpo_advantage(rewards: np.ndarray) -> np.ndarray:
    """GRPO: advantage = (reward - group mean) / group std — no critic needed (Rule 4)."""
    return (rewards - rewards.mean()) / (rewards.std() + 1e-8)

if __name__ == "__main__":
    lp_old = np.log(np.array([0.2, 0.5, 0.3]))
    lp_new = np.log(np.array([0.3, 0.4, 0.3]))
    adv = np.array([1.0, -0.5, 0.2])
    print("PPO objective:", round(ppo_objective(lp_old, lp_new, adv), 4))
    group = np.array([0.1, 0.9, 0.5, 0.2])
    print("GRPO advantages:", np.round(grpo_advantage(group), 2))
```

### 4. Agent Execution Directives
* **When sizing RLHF infra:** account for four models in flight; offload the frozen two (Rules 3, 5).
* **When choosing PPO vs GRPO:** default to GRPO for large models (no critic); use PPO when a value baseline is justified.
* **When reward rises but quality drops:** suspect reward hacking — check KL and response-length/entropy (Rule 6).
