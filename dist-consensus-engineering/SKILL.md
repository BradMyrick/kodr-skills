---
name: dist-consensus-engineering
description: Decision guide for choosing a consensus protocol — Paxos, Raft, BFT (PBFT/HotStuff), or Nakamoto (PoW/PoS) — by fault model, finality, and scale. Use when selecting or comparing consensus for a distributed system. Foundational theory in cs-lamport-1998 / cs-ongaro-2014 / cs-castro-1999 / cs-lamport-1982 / cs-nakamoto-2008.
version: 1.0.0
---

# Skill: Consensus Engineering — Choosing the Right Protocol
## System Reference: Fault-Model → Protocol Decision Tree (RFC-Style Engineering Spec)

### 1. Core Model
Consensus makes independent nodes **agree on a value (or a log)**. The right protocol is dictated by your **fault model**, **finality** need, and **scale** — never by fashion.

**Decision drivers:**
* **Fault model:** crash-only (nodes halt/recover) vs **Byzantine** (nodes lie). Byzantine costs ~3× nodes.
* **Trust model:** permissioned (known members) vs **permissionless** (open, sybil-susceptible).
* **Finality:** absolute (committed ⇒ never reverted) vs probabilistic.
* **Scale & membership:** small stable committee vs thousands of rotating validators.

**The map:**
| Need | Protocol | Nodes | Finality | Paper |
|---|---|---|---|---|
| Crash-fault, permissioned, understandable | **Raft** | $2f+1$ | absolute | `cs-ongaro-2014` |
| Crash-fault, proven/old, hard | **Paxos / Multi-Paxos** | $2f+1$ | absolute | `cs-lamport-1998` |
| Byzantine, permissioned committee | **PBFT / HotStuff** | $3f+1$ | absolute | `cs-castro-1999` |
| Permissionless, open, sybil-resistant | **Nakamoto (PoW)** / **PoS+BFT** | many | probabilistic / economic | `cs-nakamoto-2008` |
| Byzantine agreement theory | oral/signature bounds | $3f+1$ | — | `cs-lamport-1982` |

**Two invariants to always state:** the **fault bound** ($2f+1$ crash / $3f+1$ Byzantine) and the **FLP caveat** — deterministic consensus with even one crash is impossible in fully asynchronous networks, so real systems add a synchrony/time-out assumption for liveness.

### 2. Operational Rules
* **Rule 1 (Fault model first):** crash-only → Raft/Paxos; any actor may lie → BFT; open membership → Nakamoto/PoS. Pick before anything else.
* **Rule 2 (Quorum bound):** crash $2f+1$; Byzantine $3f+1$. Derive $f$ from $n$ and quote it.
* **Rule 3 (Finality matches the consumer):** payments/SETTLEMENT need absolute; best-effort ordering may accept probabilistic.
* **Rule 4 (FLP ⇒ partial synchrony):** every real protocol assumes eventual message delivery (a timeout/GST) for liveness; state it.
* **Rule 5 (Leader ≠ consensus):** Raft/Paxos/Multi-Paxos elect a leader for throughput; the safety does not depend on the leader being honest (crash) — but a Byzantine leader needs a view-change/election proof (PBFT/HotStuff).
* **Rule 6 (HotStuff over PBFT at scale):** PBFT is $O(n^2)$ messages; HotStuff is $O(n)$ via threshold signatures + linear voting — choose HotStuff for large committees.

### 3. Reference Implementation (Python — decision engine)
```python
from dataclasses import dataclass

@dataclass
class Requirement:
    byzantine: bool          # can nodes lie?
    permissionless: bool     # open membership?
    absolute_finality: bool  # committed never reverted?
    committee_size: int      # number of participants

def choose(r: Requirement) -> str:
    if r.permissionless:
        return "Nakamoto PoW or PoS+BFT (probabilistic/economic finality)"   # cs-nakamoto-2008
    if r.byzantine:
        if r.committee_size > 50:
            return "HotStuff (linear BFT)"                                     # 3f+1
        return "PBFT (practical BFT)"                                          # cs-castro-1999
    if r.absolute_finality:
        return "Raft (or Multi-Paxos if you need its maturity)"                # cs-ongaro-2014
    return "Raft by default; Paxos if you have a reason"

def fault_bound(byzantine: bool, n: int) -> int:
    return (n - 1) // 3 if byzantine else (n - 1) // 2

if __name__ == "__main__":
    print(choose(Requirement(False, False, True, 5)))        # Raft
    print(choose(Requirement(True, False, True, 7)))         # PBFT
    print(choose(Requirement(True, True, False, 10_000)))    # Nakamoto/PoS
    print("f tolerable, n=7 byzantine:", fault_bound(True, 7))   # 2
```

### 4. Agent Execution Directives
* **When asked "what consensus?":** run the decision tree (fault model → trust → finality → scale) and return the protocol + paper + fault bound.
* **Never** recommend a Byzantine protocol for a crash-only system, or a crash-only protocol for adversarial actors.
* **Always** state the FLP caveat and the synchrony assumption your liveness relies on.
