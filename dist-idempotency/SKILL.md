---
name: dist-idempotency
description: Idempotency keys, deduplication, and exactly-once semantics for retries and message delivery. Use when any operation may be retried or delivered more than once. NOT a substitute for transactions — use dist-transactions for multi-step atomicity.
version: 1.0.0
---

# Skill: Idempotency & Exactly-Once
## System Reference: Idempotency Keys + Dedup Store (RFC-Style Engineering Spec)

### 1. Core Model
Networks retry, consumers redeliver, and clients double-click. An operation is **idempotent** if applying it $k \geq 1$ times has the same effect as applying it once. Making every retried operation idempotent is how you get **exactly-once** semantics — which is *never* delivered by the network; it is always **at-least-once delivery + idempotent processing**.

**The idempotency-key pattern:** the caller attaches a unique key (UUID, or `client_id + sequence`) to the request; the server records the key + the result the **first time**, and on a retry returns the stored result instead of re-executing. Payment systems (Stripe) and queues (SQS dedup) rely on this.

**Requirements for correctness:**
1. The key is unique per logical operation and supplied by the caller (server can't invent it).
2. The check-and-store is **atomic** (a single transaction/CAS) — else a race double-charges.
3. The stored result is returned verbatim on retry — including failures (don't re-invoke on a stored failure).

**Natural idempotency:** some operations are idempotent by construction (PUT to a fixed resource, "set x=5", add-to-set). Exploit it before building a key store.

**Dedup windows:** keys live in a TTL store long enough to cover the max retry window; a key that expires before a delayed retry lets a duplicate through.

### 2. Operational Rules
* **Rule 1 (Exactly-once = idempotent consumer):** never claim single-delivery; make the effect idempotent instead.
* **Rule 2 (Caller supplies the key):** the client generates the idempotency key; the server stores it.
* **Rule 3 (Atomic check-and-store):** the "seen?" check and the effect (or the stored result) happen in one transaction/CAS — else races double-execute.
* **Rule 4 (Replay the stored result, even failures):** a retry of a failed op must return the same failure, not re-execute.
* **Rule 5 (TTL covers the retry window):** keep keys at least as long as the longest possible retry/redelivery.
* **Rule 6 (Prefer natural idempotency):** model effects as "set" / "add-to-set" where possible; keys are the fallback.

### 3. Reference Implementation (Python — idempotent handler)
```python
import time
from dataclasses import dataclass, field

@dataclass
class IdempotencyStore:
    """Records key -> (result, ts). Real impl: a DB row or Redis SETNX with TTL."""
    table: dict = field(default_factory=dict)
    ttl_s: float = 86_400

    def _live(self, key, now):
        rec = self.table.get(key)
        if rec and now - rec[1] > self.ttl_s:        # Rule 5: expired -> treat as unseen
            del self.table[key]; return None
        return rec

    def execute(self, key: str, fn, now: float | None = None):
        now = now if now is not None else time.time()
        rec = self._live(key, now)
        if rec is not None:
            return rec[0]                              # Rule 4: replay stored result (incl. failures)
        result = fn()                                  # Rule 3: in real code this + the insert is ONE tx/CAS
        self.table[key] = (result, now)
        return result

# Simulate a non-idempotent effect guarded by the store.
def charge(card: str, amount: int):
    def _do():
        print(f"  charging {card} ${amount}")         # would double-charge WITHOUT the guard
        return {"charged": amount}
    return _do

store = IdempotencyStore()
key = "req-abc-123"
r1 = store.execute(key, charge("4242", 100))           # executes, prints once
r2 = store.execute(key, charge("4242", 100))           # replays r1, does NOT print/charge again
assert r1 == r2
```

### 4. Agent Execution Directives
* **For any retried effect:** add an idempotency key + atomic dedup; prove the check-and-store is atomic (Rule 3).
* **When reviewing:** confirm stored failures are replayed (Rule 4) — re-invoking on a stored failure is a classic double-charge bug.
* **When the key can expire late:** size the TTL above the max redelivery window (Rule 5).
