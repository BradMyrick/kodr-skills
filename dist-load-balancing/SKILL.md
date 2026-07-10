---
name: dist-load-balancing
description: Load balancing, backpressure, circuit breakers, rate limiting, and capacity math (Little's law). Use when distributing traffic, shedding overload, or isolating failing dependencies. NOT for data partitioning — use dist-partitioning.
version: 1.0.0
---

# Skill: Load Balancing & Overload Control
## System Reference: LB Algorithms + Backpressure + Circuit Breakers + Little's Law (RFC-Style Engineering Spec)

### 1. Core Model
A load balancer spreads requests across replicas to maximize throughput and minimize latency; overload control keeps a system **alive** when demand exceeds capacity. Both are mandatory — balancing without shedding turns overload into a cascade.

**LB algorithms:** round-robin (cheap, ignores load), least-connections (reacts to slow replicas), consistent-hashing (`dist-partitioning`, for sticky/cache-friendly placement), and **power-of-two-choices** (pick 2 random, send to the less-loaded — near-optimal without global state).

**Backpressure** is the honest signal "I'm full." A **bounded queue/channel** applies it: when full, the producer is blocked/dropped rather than queuing unboundedly into OOM. Accept it; buffering hides overload until catastrophic failure.

**Circuit breaker:** track a dependency's failures; when error-rate/latency crosses a threshold, **open** (fail-fast for a cooldown) instead of piling on a dying service; periodically **half-open** to probe recovery; **close** when healthy. Prevents cascading failures.

**Rate limiting:** token bucket (bursty) / leaky bucket (smooth) / sliding window; enforce per-tenant to protect noisy-neighbor fairness.

**Little's law:** $L = \lambda W$ — the number in system = arrival rate × mean residence time. It links throughput, latency, and concurrency; it's how you size capacity and reason about saturation.

### 2. Operational Rules
* **Rule 1 (Bounded queues apply backpressure):** never buffer unboundedly; reject/block when full rather than OOM.
* **Rule 2 (Circuit breaker per dependency):** fail-fast a failing dependency; don't let its latency drag your threads down.
* **Rule 3 (Power-of-two-choices beats round-robin):** near-optimal load with two random samples and no global state.
* **Rule 4 (Rate-limit per tenant):** protect fairness; a single noisy tenant must not starve others.
* **Rule 5 (Size with Little's law):** derive required concurrency $L = \lambda W$ from your SLO latency $W$ and target throughput $\lambda$.
* **Rule 6 (Shed load intentionally):** under overload, shed low-priority work (503/429 + backoff) to keep critical paths alive.

### 3. Reference Implementation (Python — circuit breaker + token bucket + Little's law)
```python
import time, random
from dataclasses import dataclass

@dataclass
class CircuitBreaker:
    threshold: float = 0.5
    cooldown_s: float = 5.0
    state: str = "closed"
    opened_at: float = 0.0
    successes: int = 0
    failures: int = 0
    def allow(self) -> bool:
        if self.state == "open":
            if time.monotonic() - self.opened_at >= self.cooldown_s:
                self.state = "half_open"           # probe
                return True
            return False                           # Rule 2: fail-fast
        return True
    def record(self, ok: bool):
        if ok: self.successes += 1
        else:  self.failures += 1
        total = self.successes + self.failures
        if total and self.failures / total >= self.threshold:
            self.state = "open"; self.opened_at = time.monotonic()
        elif self.state == "half_open" and ok:
            self.state = "closed"; self.successes = self.failures = 0   # recovered

class TokenBucket:
    def __init__(self, rate_per_s: float, burst: int):
        self.rate = rate_per_s; self.burst = burst; self.tokens = burst; self.t = time.monotonic()
    def allow(self) -> bool:                       # Rule 4
        now = time.monotonic(); self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if self.tokens >= 1: self.tokens -= 1; return True
        return False

def littles_concurrency(arrival_rate: float, mean_residence_s: float) -> float:
    return arrival_rate * mean_residence_s         # Rule 5: L = lambda * W

def p2c_choice(loads: list[int]) -> int:
    """Power-of-two-choices: sample 2, return the less-loaded (Rule 3)."""
    a, b = random.sample(range(len(loads)), 2)
    return a if loads[a] <= loads[b] else b
```

### 4. Agent Execution Directives
* **When sizing a service:** compute concurrency via Little's law from your SLO latency and target QPS.
* **When a dependency is flaky:** add a circuit breaker before you add retries.
* **Under load spikes:** ensure backpressure (bounded queues) and intentional shedding (503/429) exist — buffering the spike is what causes OOM cascades.
