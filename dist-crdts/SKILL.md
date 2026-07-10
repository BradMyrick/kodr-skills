---
name: dist-crdts
description: Conflict-free Replicated Data Types (state- and operation-based) for eventually consistent, partition-tolerant merges — G-Counter, LWW-Register, OR-Set. Use when designing offline-first or AP stores that must merge without coordination. NOT for strongly consistent data — use dist-consistency.
version: 1.0.0
---

# Skill: CRDTs (Conflict-Free Replicated Data Types)
## System Reference: Convergent + Commutative Replicated State (RFC-Style Engineering Spec)

### 1. Core Model
A **CRDT** is a data structure whose concurrent updates always **merge deterministically** without coordination — replicas converge regardless of operation order or network delays. The trick: updates are **commutative**, **associative**, and **idempotent** ($a \vee a = a$), with a least-upper-bound join $\vee$ that is monotonic.

**Two flavors:**
* **State-based (CvRDT):** replicas ship their full state; merge = pairwise join $\vee$. Simple, message-heavy.
* **Operation-based (CmRDT):** replicas ship operations (delivered reliably, causally ordered); applying any order converges. Light messages, needs reliable causal delivery.

**Canonical types:**
* **G-Counter:** each replica holds a per-node counter; value = $\sum$; merge = element-wise `max`. Monotonic, never decrements.
* **PN-Counter:** two G-Counters (increments + decrements) ⇒ supports decrement.
* **LWW-Register:** last-writer-wins value tagged with a timestamp/HLC; merge = pick higher timestamp.
* **OR-Set (Observed-Remove Set):** add tags an element with a unique tag; remove removes only *observed* tags ⇒ concurrent add/remove don't conflict.

CRDTs trade strong consistency for **high availability** — perfect for AP stores (Riak, Redis CRDT, Yjs, automerge) and offline-first/collaborative editing.

### 2. Operational Rules
* **Rule 1 (Join must form a semilattice):** $\vee$ is commutative, associative, idempotent, and monotonic — if not, replicas diverge.
* **Rule 2 (Metadata grows; garbage-collect deliberately):** G-Counters/sets grow with replica count and add-tags; plan tombstone/tag compaction or accept growth.
* **Rule 3 (Use HLC, not wall-clock, for LWW):** physical timestamps skew; an HLC timestamp gives causal LWW (`dist-consistency`).
* **Rule 4 (Op-based needs causal delivery):** CmRDTs assume reliable, causal-ordered delivery — else fall back to state-based.
* **Rule 5 (CRDTs are AP):** pick them when availability/partition-tolerance beats strong consistency; don't use for money/invariants that need coordination.

### 3. Reference Implementation (Python — G-Counter + LWW-Register + OR-Set)
```python
from dataclasses import dataclass, field

class GCounter:
    """Per-replica monotonic counter; merge = element-wise max."""
    def __init__(self): self.counts: dict[str, int] = {}
    def increment(self, replica: str): self.counts[replica] = self.counts.get(replica, 0) + 1
    def value(self) -> int: return sum(self.counts.values())
    def merge(self, other: "GCounter"):
        for k, v in other.counts.items(): self.counts[k] = max(self.counts.get(k, 0), v)

@dataclass
class LWWRegister:
    """Last-writer-wins; tie-break by replica id for determinism."""
    value: object = None
    ts: int = 0
    replica: str = ""
    def set(self, value, ts, replica):
        if (ts, replica) >= (self.ts, self.replica):     # Rule 3: use HLC ts in practice
            self.value, self.ts, self.replica = value, ts, replica
    def merge(self, other: "LWWRegister"):
        if (other.ts, other.replica) >= (self.ts, self.replica):
            self.value, self.ts, self.replica = other.value, other.ts, other.replica

class ORSet:
    """Add tags uniquely; remove only observed tags -> concurrent add/remove converge."""
    def __init__(self): self.elements: dict[object, set] = {}   # value -> set of tags
    def add(self, value, tag): self.elements.setdefault(value, set()).add(tag)
    def remove(self, value): self.elements.pop(value, None)      # removes observed tags only
    def merge(self, other: "ORSet"):
        for v, tags in other.elements.items(): self.elements.setdefault(v, set()).update(tags)
    def read(self): return set(self.elements)

if __name__ == "__main__":
    a, b = GCounter(), GCounter()
    a.increment("A"); a.increment("A"); b.increment("B")
    a.merge(b); assert a.value() == 3                       # converged
    x, y = LWWRegister(), LWWRegister(); x.set("old", 1, "A"); y.set("new", 2, "B")
    x.merge(y); assert x.value == "new"
```

### 4. Agent Execution Directives
* **When designing an AP store:** model the data as a CRDT whose join is a provable semilattice (Rule 1).
* **When using LWW:** timestamp with an HLC, never a skewed wall clock.
* **When metadata grows:** plan tag/tombstone compaction or bound the replica set.
