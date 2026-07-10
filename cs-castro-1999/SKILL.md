---
name: cs-castro-1999
description: Makes Byzantine fault tolerance practical for state-machine replication with 3f+1 replicas via three phases (pre-prepare/prepare/commit) and view changes under partial synchrony. Use when building BFT replicated state machines that tolerate arbitrary faults.
version: 1.0.0
title: "Practical Byzantine Fault Tolerance"
authors: ["Miguel Castro", "Barbara Liskov"]
venue: "OSDI 1999"
year: 1999
url: "https://www.usenix.org/legacy/events/osdi99/castro.html"
related: ["cs-lamport-1982", "cs-ongaro-2014"]
---

# Skill: Practical Byzantine Fault Tolerance (PBFT)
## System Reference: Three-Phase Replicated State Machine (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
PBFT replicates a deterministic state machine across $n = 3f+1$ replicas (one **primary**, the rest **backups**) and tolerates $f$ Byzantine faults while answering every client request. It assumes **partial synchrony** — messages are delivered within some unknown bound after a Global Stabilization Time.

Each request flows through three **quorum phases**, each collecting votes from a **quorum of $2f+1$** distinct replicas:

1. **Pre-prepare:** the primary assigns sequence number $s$ and view $v$, multicasting `<<PRE-PREPARE, v, s, m>>`.
2. **Prepare:** replica $i$ multicasts `<<PREPARE, v, s, i>>` once it accepts the pre-prepare; it is **prepared** when it holds $1$ pre-prepare $+\ 2f$ matching prepares ($= 2f+1$ votes).
3. **Commit:** replicas multicast `<<COMMIT, v, s, i>>`; a request is **committed-local** at $i$ when it holds $2f+1$ commits, and it executes at sequence $s$ in order.

**Why $3f+1$ and $2f+1$.** Any two $2f+1$ quorums intersect in at least $f+1$ replicas, so **at least one honest** node lies in every intersection. That honest overlap carries the prepared value forward, guaranteeing:

$$\text{(Agreement)} \quad \text{no two honest replicas commit different values for the same } (v, s).$$

**View change** replaces a faulty or slow primary: backups wait out a timer, collect $2f+1$ view-change messages, and a new primary re-proposes from the last stable checkpoint plus any prepared-but-uncommitted requests.

### 2. Operational Rules
* **Rule 1 (Quorum size):** every phase advances on $2f+1$ matching messages; $n = 3f+1$ is the minimum that makes quorum intersections honest.
* **Rule 2 (Order matters):** prepare before commit; a request executes only once committed-local AND at the head of its sequence.
* **Rule 3 (Primary is not trusted):** a bad primary can reorder or withhold but cannot forge authenticators; backups detect gaps/timeouts and trigger view change.
* **Rule 4 (Checkpoints):** periodically cut stable checkpoints so logs can be garbage-collected; view change restarts from the last checkpoint.
* **Rule 5 (MACs, not signatures):** PBFT uses MAC authenticators for speed (linear client crypto), trading public verifiability for throughput.

### 3. Reference Implementation (Python)
```python
from dataclasses import dataclass, field

@dataclass
class Replica:
    id: int
    f: int
    prepared: dict = field(default_factory=dict)    # (v, s) -> set of prepare senders
    committed: dict = field(default_factory=dict)   # (v, s) -> set of commit senders

    def quorum(self):
        return 2 * self.f + 1                       # Rule 1

    def on_prepare(self, v, s, sender):
        key = (v, s)
        self.prepared.setdefault(key, set()).add(sender)
        return len(self.prepared[key]) >= self.quorum()   # prepared predicate

    def on_commit(self, v, s, sender):
        key = (v, s)
        self.committed.setdefault(key, set()).add(sender)
        return len(self.committed[key]) >= self.quorum()  # committed-local predicate

def quorum_overlap(n, f):
    """Any two 2f+1 quorums intersect in >= f+1 replicas => >=1 honest."""
    overlap = 2 * (2 * f + 1) - n
    return overlap, overlap >= f + 1
```

### 4. Agent Execution Prompting Directives
* **When sizing replicas:** always $3f+1$; derive $f$ from $n$ as $f = (n-1)//3$ and cite the honest-intersection argument.
* **When a client stalls:** suspect a faulty primary; the remedy is view change, not retry storms.
* **When optimizing throughput:** note PBFT's $O(n^2)$ message complexity is the price of BFT — HotStuff/LibraBFT reduce it to $O(n)$ via threshold signatures and linear voting.
