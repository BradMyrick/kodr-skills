---
name: dist-consistency
description: Consistency models (linearizable, serializable, causal, read-your-writes, eventual), CAP/PACELC trade-offs, and logical/vector clocks. Use when choosing or defending a consistency guarantee for a distributed system. NOT for the consensus algorithm itself — use dist-consensus-engineering.
version: 1.0.0
---

# Skill: Consistency Models, CAP & Clocks
## System Reference: The Consistency Spectrum + CAP/PACELC (RFC-Style Engineering Spec)

### 1. Core Model
A **consistency model** is the contract a system gives its clients about how recent/correct their reads are. Stronger = easier to reason about = slower/less available.

| Model | Guarantee | Cost |
|---|---|---|
| **Linearizable** | every read returns the latest write; ops appear in one real-time order | needs a quorum/leader + sync; not available under partition |
| **Serializable** | a concurrent execution equivalent to some serial one | isolation overhead; may allow stale reads vs real-time |
| **Causal** | preserves causality (if a→b, everyone sees a before b) | needs vector clocks; concurrent writes may conflict |
| **Read-your-writes** | a client always sees its own writes | session stickiness / version tokens |
| **Eventual** | if no new writes, replicas eventually converge | fastest, most available; reads can be arbitrarily stale |

**CAP.** Under a network **partition** you must choose: **C** (refuse stale requests) or **A** (serve, risk inconsistency). When *not* partitioned you can have both; so the real statement is "during a partition, pick C or A."

**PACELC.** Extends CAP: **P**artition → choose **C** or **A**; **E**lse (no partition) → choose **L**atency or **C**. A system like Cassandra is PA/EL; Spanner is CP/EC-ish. Always state the no-partition trade-off too.

**Clocks.** Wall-clock time is unreliable (skew, non-monotonic). To reason about order:
* **Lamport clocks** (`cs-lamport-1978`): scalar total order, no concurrency detection.
* **Vector clocks**: detect causality and concurrency ($a \| b$).
* **HLC (Hybrid Logical Clock)**: wall-clock + logical, gives physical-ish timestamps with causality — the Spanner/TrueTime family.

### 2. Operational Rules
* **Rule 1 (State the model explicitly):** never ship a data store without naming its consistency guarantee for reads and writes.
* **Rule 2 (CAP is about partitions):** the choice bites only during a partition; pick based on your failure semantics, not a slogan.
* **Rule 3 (Don't trust wall clocks):** use HLC/vector clocks for ordering; reserve TrueClock/NTP only where bounded skew is provable.
* **Rule 4 (Causality is cheap-ish):** causal consistency gives most of the value of linearizability at much higher availability — prefer it over eventual when clients reason about "happened-after."
* **Rule 5 (Read-your-writes is a UX contract):** session-sticky routing or version vectors; a user who just wrote must read it back.

### 3. Reference Implementation (Python — vector clock + quorum consistency check)
```python
def meet_quorum(r: int, w: int, n: int) -> bool:
    """Strong (stale-free) reads require R + W > N (quorum intersection)."""
    return r + w > n

class VClock:
    """Vector clock: detect causality (a->b) vs concurrency (a || b)."""
    def __init__(self): self.c: dict[str, int] = {}
    def bump(self, node: str): self.c[node] = self.c.get(node, 0) + 1
    def merge(self, other: "VClock"):
        for k, v in other.c.items(): self.c[k] = max(self.c.get(k, 0), v)

def compare(a: VClock, b: VClock) -> str:
    def dominates(x, y): return all(x.c.get(k, 0) >= v for k, v in y.c.items()) and x.c != y.c
    if a.c == b.c: return "equal"
    if dominates(a, b): return "a-before-b"
    if dominates(b, a): return "b-before-a"
    return "concurrent"                        # conflicting concurrent writes

if __name__ == "__main__":
    assert meet_quorum(r=2, w=3, n=4) and not meet_quorum(r=2, w=2, n=4)
    a, b = VClock(), VClock()
    a.bump("n1"); a.bump("n1")
    b.merge(a); b.bump("n2")                   # b saw a -> b is after a
    print(compare(a, b))                        # a-before-b
```

### 4. Agent Execution Directives
* **When proposing a store:** name the read+write consistency model and the PACELC trade-off (Rules 1–2).
* **When ordering events:** reach for vector/HLC clocks, not wall time (Rule 3).
* **When clients care about their own writes:** guarantee read-your-writes via session routing.
