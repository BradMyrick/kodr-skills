---
name: dist-transactions
description: Distributed transactions and isolation — 2PC/3PC, sagas, the outbox pattern, exactly-once delivery, and isolation levels. Use when coordinating multi-service or multi-shard writes. NOT for consensus — use dist-consensus-engineering.
version: 1.0.0
---

# Skill: Distributed Transactions
## System Reference: 2PC / Saga / Outbox / Exactly-Once (RFC-Style Engineering Spec)

### 1. Core Model
A transaction spans multiple services/shards and must be **atomic** (all-or-nothing), **isolated**, and **durable**. Doing this across independent stores is the hard problem of distributed data.

**Two-phase commit (2PC).** A coordinator asks participants to PREPARE (they lock + promise), then COMMIT/ABORT. Provides atomicity but: the coordinator is a single point of failure, PREPARE holds locks (low availability), and a coordinator crash mid-commit **blocks** participants indefinitely. 3PC removes the blocking case under synchrony but is rarely used (cost/assumptions).

**Saga.** A long-lived transaction is a sequence of local sub-transactions; each has a **compensating action** that undoes it. Failure ⇒ run compensations backwards. No global isolation — design for it with semantic locks or commutativity.

**Outbox pattern.** Don't do "write to DB + publish to queue" as two operations (the dual-write problem — one can fail). Instead: write the DB row and the outbox row **in one local transaction**; a separate process reads the outbox and publishes. This gives **exactly-once** delivery semantics (at-least-once publish + idempotent consumer).

**Exactly-once** is always *at-least-once delivery + idempotent processing*; true single-delivery across failures is impossible. Use **idempotency keys** (`dist-idempotency`).

**Isolation levels.** Read-uncommitted → serializable; stronger isolation prevents anomalies (lost update, write skew) but reduces concurrency.

### 2. Operational Rules
* **Rule 1 (Avoid 2PC when you can):** it's blocking and brittle; prefer sagas + outbox for cross-service work, 2PC only inside one DB/vendor.
* **Rule 2 (Outbox for DB+message):** never dual-write a store and a queue; outbox them in one transaction.
* **Rule 3 (Exactly-once = idempotent consumer):** make consumers idempotent via keys; don't chase impossible single-delivery.
* **Rule 4 (Sagas need compensation):** every step has a defined undo; design for partial states and commutativity since there's no global lock.
* **Rule 5 (Choose isolation deliberately):** pick the weakest level that prevents your specific anomaly; serializable is safest but slowest.
* **Rule 6 (Idempotency keys for retries):** every retried external effect carries a unique key the receiver dedups on.

### 3. Reference Implementation (Python — saga coordinator + outbox)
```python
from dataclasses import dataclass, field

@dataclass
class Saga:
    """Forward actions + compensations; on failure, unwind completed steps."""
    steps: list  # list of (name, do_fn, compensate_fn)
    done: list = field(default_factory=list)

    def run(self, ctx: dict):
        try:
            for name, do_fn, comp_fn in self.steps:
                do_fn(ctx)
                self.done.append((name, comp_fn))
        except Exception as e:
            self._compensate(ctx)              # Rule 4: unwind on failure
            raise

    def _compensate(self, ctx):
        for _, comp_fn in reversed(self.done):
            try: comp_fn(ctx)
            except Exception: pass             # log; best-effort unwind

@dataclass
class Outbox:
    """Write a row and a pending message in one local tx; a relay publishes later."""
    rows: list = field(default_factory=list)
    pending: list = field(default_factory=list)

    def in_one_transaction(self, row, message):
        self.rows.append(row)
        self.pending.append(message)           # Rule 2: atomic local write

    def relay(self):
        msgs, self.pending = self.pending, []  # a poller/consumer drains and publishes
        return msgs

def charge(ctx): ctx["charged"] = True
def refund(ctx): ctx["charged"] = False
def ship(ctx):
    if ctx.get("fail"): raise RuntimeError("ship failed")
    ctx["shipped"] = True
def unship(ctx): ctx["shipped"] = False

if __name__ == "__main__":
    saga = Saga([("charge", charge, refund), ("ship", ship, unship)])
    try:
        saga.run({"fail": True})
    except RuntimeError:
        pass                                   # charged then refunded (compensated)
```

### 4. Agent Execution Directives
* **For cross-service writes:** sketch the saga + compensations and the outbox; never dual-write.
* **For message consumers:** verify an idempotency-key check precedes the effect.
* **For 2PC:** flag the blocking-window risk and the coordinator HA requirement before recommending it.
