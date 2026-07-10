---
name: cs-lamport-1998
description: Achieves distributed consensus among independent nodes via majority quorums across two ballot phases (Paxos). Use when implementing consensus, leader election, or reasoning about safety vs liveness in asynchronous crash-stop systems.
version: 1.0.0
title: "The Part-Time Parliament"
authors: ["Leslie Lamport"]
venue: "ACM Transactions on Computer Systems, 16(2)"
year: 1998
url: "https://doi.org/10.1145/279227.279229"
related: ["cs-lamport-1978", "cs-lamport-1982", "cs-ongaro-2014"]
---

# Skill: Paxos Consensus via Majority Ballots
## System Reference: The Synod Protocol (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Consensus means getting independent processes to **agree on a single value** despite crashes and message delays. Paxos separates three roles — **Proposers** (drive rounds), **Acceptors** (form the quorum/memory), **Learners** (learn the chosen value). A round carries a totally-ordered **ballot number** $n$.

Two phases per round:

**Phase 1 (Prepare / Promise).** Proposer broadcasts `Prepare(n)`. An acceptor promises to ignore ballots $< n$ and replies `Promise(n, n_a, v_a)` — the number $n_a$ and value $v_a$ of the highest-numbered proposal it has already accepted (or $\bot$).

**Phase 2 (Accept / Accepted).** The proposer picks its value as the value of the highest-$n_a$ promise received (or its own if all $\bot$) and broadcasts `Accept(n, v)`. An acceptor accepts iff it hasn't promised a higher ballot, then informs learners.

**Safety invariants** (hold under arbitrary reordering, loss, and duplication of messages):
1. *Agreement:* at most one value is ever chosen.
2. *Validity:* only proposed values can be chosen.

Agreement follows from the **quorum-intersection lemma**: any two majorities share at least one acceptor, and the "highest accepted value" rule forces later proposers to re-propose any already-chosen value.

**Liveness:** Paxos guarantees safety under pure asynchrony but makes progress only with an **eventually-stable leader** and reliable delivery to a majority. (Deterministic consensus with even one crash is impossible in a fully asynchronous system — the FLP result.)

### 2. Operational Rules
* **Rule 1 (Ballot monotonicity):** acceptors act only on ballots $\ge$ their last promise; proposers use monotonically increasing $n$.
* **Rule 2 (Quorum = majority):** progress requires responses from a strict majority; never accept with fewer.
* **Rule 3 (Value inheritance):** once any value is accepted, a Phase-2 proposer MUST adopt the highest-numbered accepted value — never overwrite a chosen value.
* **Rule 4 (Leader for liveness):** safety holds without a leader, but liveness needs an eventual stable leader (Multi-Paxos collapses Phase 1 across a leadership lease).

### 3. Reference Implementation (Python)
```python
from dataclasses import dataclass

@dataclass(order=True)
class Ballot:
    num: int
    leader_id: int

@dataclass
class Acceptor:
    promised: Ballot = None
    accepted_n: Ballot = None
    accepted_v: object = None

    def prepare(self, b: Ballot):
        if self.promised is None or b > self.promised:
            self.promised = b
        return (self.accepted_n, self.accepted_v) if self.promised == b else None

    def accept(self, b: Ballot, v):
        if self.promised is None or b >= self.promised:    # Rule 1
            self.accepted_n, self.accepted_v = b, v
            return True
        return False

@dataclass
class Proposer:
    me: int
    n: int = 0
    def next_ballot(self) -> Ballot:
        self.n += 1
        return Ballot(self.n, self.me)

def paxos_round(proposer: Proposer, acceptors: list, value):
    b = proposer.next_ballot()
    promises = [(a, a.prepare(b)) for a in acceptors]
    if len(promises) <= len(acceptors) // 2:        # Rule 2: need majority
        return None
    accepted = [p for (_, p) in promises if p and p[0]]
    v = max(accepted, key=lambda p: p[0])[1] if accepted else value   # Rule 3
    chosen = sum(1 for a in acceptors if a.accept(b, v)) > len(acceptors) // 2
    return v if chosen else None
```

### 4. Agent Execution Prompting Directives
* **When implementing:** never skip value inheritance (Rule 3) — it is the subtle bug that silently breaks agreement.
* **When debugging stalls:** check for dueling proposers; without an eventual single leader, ballots starve each other (no progress, though safety holds).
* **When extending to logs:** Multi-Paxos reuses one Phase 1 across a stable leadership lease for many slots — the common production form.
