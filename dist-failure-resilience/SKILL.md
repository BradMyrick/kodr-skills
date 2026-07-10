---
name: dist-failure-resilience
description: Failure detection (heartbeat, Φ-accrual), recovery objectives (RTO/RPO), chaos/fault injection, and retry/backoff/timeouts. Use when designing liveness, timeout budgets, or recovery objectives. NOT for consensus membership — use dist-consensus-engineering.
version: 1.0.0
---

# Skill: Failure Detection & Resilience
## System Reference: Φ-Accrual Detector + RTO/RPO + Retry Budgets (RFC-Style Engineering Spec)

### 1. Core Model
In a distributed system, **failures are the norm**, not the exception. You cannot reliably *detect* a crash — you can only observe the *absence of a heartbeat*, which is indistinguishable from a slow network. Good detectors quantify this uncertainty.

**Φ-accrual failure detector** (Hayashibara et al.): instead of a hard "alive/dead" threshold, output a **suspicion level** $\phi$ — the expected number of false suspicions per second given recent inter-arrival times. A node is marked suspected when $\phi$ crosses a threshold (e.g. 8). This adapts to network conditions and avoids both flapping and slow detection.

**Recovery objectives:**
* **RTO** (Recovery Time Objective): max acceptable downtime.
* **RPO** (Recovery Point Objective): max acceptable data loss (how stale backups/replicas may be).
These drive replication factor, failover automation, and backup cadence — not the other way around.

**Resilience patterns:**
* **Timeouts everywhere** — every call has a deadline; no infinite waits.
* **Backoff with jitter** — exponential + random jitter to avoid thundering-herd retries.
* **Retries bounded by a budget** — cap total retries/time to avoid amplifying load into a DoS.
* **Circuit breaker** — stop calling a failing dependency (`dist-load-balancing`).
* **Chaos/fault injection** — proactively kill nodes/partitions in prod-like to find gaps.

### 2. Operational Rules
* **Rule 1 (Φ over hard timeouts for membership):** accrual detectors adapt to skew; use them for consensus/group-membership suspicions.
* **Rule 2 (Every call has a deadline):** no RPC without a timeout; budget the total across a call chain.
* **Rule 3 (Backoff + jitter):** exponential with full/equal jitter; never retry in lockstep (causes synchronized storms).
* **Rule 4 (Retry budget):** cap retries per request and globally; a retry storm is a self-inflicted DoS.
* **Rule 5 (RTO/RPO drive the design):** state the objectives first, then derive replication, failover, and backup cadence.
* **Rule 6 (Inject failures regularly):** game-days/chaos find the gaps your happy-path tests miss.

### 3. Reference Implementation (Python — Φ-accrual + backoff-with-jitter)
```python
import math, random, statistics

def phi_accrual(arrivals_ms: list[float], now_ms: float, elapsed_since_last: float) -> float:
    """Suspicion level from recent inter-arrival times (log-normal approximation)."""
    if len(arrivals_ms) < 2:
        return 0.0
    mean = statistics.mean(arrivals_ms)
    var = statistics.pvariance(arrivals_ms) or 1.0
    # probability that a heartbeat is this late, assuming past distribution
    z = (elapsed_since_last - mean) / math.sqrt(var)
    p_late = 1.0 / (1.0 + math.exp(z))
    if p_late <= 0.0:
        return float("inf")
    return -math.log10(p_late)                 # phi grows as the absence becomes improbable

def backoff_with_jitter(attempt: int, base_ms: int = 100, cap_ms: int = 30_000) -> float:
    """Full-jitter exponential backoff (Rule 3)."""
    exp = min(cap_ms, base_ms * (2 ** attempt))
    return random.uniform(0, exp)              # full jitter desynchronizes retries

class RetryBudget:
    """Global cap on retries (Rule 4)."""
    def __init__(self, max_per_sec: int = 10): self.tokens = max_per_sec; self.max = max_per_sec
    def allow(self) -> bool:
        if self.tokens <= 0: return False
        self.tokens -= 1; return True
    def refill(self, per_sec): self.tokens = min(self.max, self.tokens + per_sec)

if __name__ == "__main__":
    arrivals = [1000, 990, 1010, 1005, 995]     # ~1s heartbeats
    print("phi at 1.1s late:", round(phi_accrual(arrivals, 0, 1100), 2))   # low
    print("phi at 5s late: ", round(phi_accrual(arrivals, 0, 5000), 2))    # high -> suspect
    print("backoffs:", [round(backoff_with_jitter(i), 1) for i in range(4)])
```

### 4. Agent Execution Directives
* **When sizing timeouts:** set per-hop deadlines that sum under the call-chain budget; never inherit infinite defaults.
* **When building membership:** use Φ-accrual, not a binary timeout, to avoid flapping.
* **When stating SLOs:** give RTO and RPO numbers, then prove the replication/failover design meets them.
