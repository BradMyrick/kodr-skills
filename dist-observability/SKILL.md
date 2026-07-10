---
name: dist-observability
description: Observability for distributed systems — metrics, tracing, structured logs (OpenTelemetry), SLI/SLO/SLA, and USE/RED analysis methods. Use when instrumenting a service, setting SLOs, or debugging latency/failures. NOT for product analytics.
version: 1.0.0
---

# Skill: Observability
## System Reference: Metrics + Distributed Tracing + Logs + SLOs (RFC-Style Engineering Spec)

### 1. Core Model
You cannot operate what you cannot see. **Observability** answers "is this healthy?" and "why is it slow/failing?" through three signals, ideally exported via **OpenTelemetry (OTel)** so they're vendor-neutral and correlated by trace IDs:

* **Metrics** (aggregated time series): counters, gauges, histograms. Cheap, ideal for alerting and dashboards.
* **Distributed tracing** (per-request spans across services): the path, timing, and causal structure of a request — essential for finding where latency/failures originate in a call graph.
* **Structured logs** (per-event records with fields + trace ID): the detailed evidence; structured (JSON) so they're filterable and join to traces.

**SLO discipline.** An **SLI** is a measured signal (e.g. "requests with p99 latency < 300ms"); an **SLO** is the target (e.g. "99.9% of requests meet the SLI over 28 days"); an **SLA** is the business consequence of breaching it. SLOs drive alerting: alert on **error budget burn rate**, not raw thresholds.

**Analysis methods:**
* **USE** (Utilization, Saturation, Errors) — for resources (CPU, disk, NIC).
* **RED** (Rate, Errors, Duration) — for services/requests.
Apply both: USE on the boxes, RED on the requests.

### 2. Operational Rules
* **Rule 1 (Three signals, correlated):** metrics + traces + logs, joined by a trace ID propagated on every hop.
* **Rule 2 (OTel everywhere):** one instrumentation standard; don't hand-roll per-vendor agents.
* **Rule 3 (Alert on SLO burn, not thresholds):** multi-window burn-rate alerts catch both fast regressions and slow bleeds without page-storms.
* **Rule 4 (Cardinality discipline):** metrics labels are bounded (no user-id/trace-id as labels) or your store explodes; high-cardinality data belongs in logs/traces.
* **Rule 5 (USE the boxes, RED the requests):** pick the method for the target — resources vs endpoints.
* **Rule 6 (p99/p99.9, not averages):** tail latency is where users suffer; report percentiles with histograms, not means.

### 3. Reference Implementation (Python — burn-rate alerting + RED/USE capture)
```python
from dataclasses import dataclass

@dataclass
class SLO:
    """Availability SLO over a window; compute error-budget burn rate."""
    target: float          # e.g. 0.999 (three nines)
    window_s: float        # e.g. 28 days

def burn_rate(good: int, total: int, target: float) -> float:
    """How many times faster than allowed we're consuming the error budget."""
    error_rate = 1 - (good / total) if total else 0.0
    allowed = 1 - target                            # the error budget fraction
    return error_rate / allowed if allowed > 0 else float("inf")

def should_page(good: int, total: int, target: float, fast_window_burn: float = 14.4,
                slow_window_burn: float = 6.0) -> bool:
    """Multi-window burn-rate alert (Rule 3): page when burning budget fast AND sustained."""
    b = burn_rate(good, total, target)
    return b >= fast_window_burn                      # combine with a slow window in real alerting

@dataclass
class RED:        # Rule 5: per-service request method
    rate: float           # requests/s
    errors: float         # error rate (0..1)
    duration_p99_s: float # p99 latency

@dataclass
class USE:        # Rule 5: per-resource method
    utilization: float    # 0..1 busy
    saturation: float     # queue length / waiting
    errors: int           # count

if __name__ == "__main__":
    # 99.9% target, observed 99.5% => burning budget 500x => page
    print("burn:", round(burn_rate(good=9950, total=10000, target=0.999), 1))
    print("page:", should_page(9950, 10000, 0.999))
```

### 4. Agent Execution Directives
* **When instrumenting:** emit RED per endpoint + USE per resource, propagate a trace ID, and use OTel (Rules 1–2, 5).
* **When alerting:** define SLOs and alert on burn rate, not a CPU threshold (Rule 3).
* **When debugging latency:** open the trace, find the slowest span, then USE the resource behind it.
