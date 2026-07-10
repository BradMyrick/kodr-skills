---
name: cs-lamport-1982
description: Solves agreement among loyal generals when some are traitorous, proving n >= 3f+1 replicas are required for f Byzantine (arbitrary) faults via oral messages. Use when designing BFT replication or reasoning about Byzantine fault tolerance bounds.
version: 1.0.0
title: "The Byzantine Generals Problem"
authors: ["Leslie Lamport", "Robert Shostak", "Marshall Pease"]
venue: "ACM Transactions on Programming Languages and Systems, 4(3)"
year: 1982
url: "https://doi.org/10.1145/357172.357176"
related: ["cs-lamport-1978", "cs-castro-1999"]
---

# Skill: Byzantine Agreement & the 3f+1 Bound
## System Reference: Oral-Messages Algorithm OM(m) (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
A commander broadcasts an order ("attack" or "retreat") to $n-1$ lieutenants; up to $f$ of all $n$ actors may be **traitors** who behave arbitrarily (Byzantine faults). Goal: all loyal lieutenants agree on the same order, and if the commander is loyal they agree on *his* order.

**Oral-messages algorithm OM($m$)** solves this for $n \ge 3f+1$ using $m = f$ rounds:
* *Base* OM(0): the commander sends its value; each lieutenant uses what it receives (a default if nothing).
* *Step* OM($m$): the commander sends $v$; each lieutenant then acts as commander for OM($m-1$), relaying $v$ to the others. After $m$ rounds, each lieutenant takes the majority value of the message tree it collected.

**Impossibility.** With oral (unsigned) messages, agreement is impossible when $n \le 3f$:
$$n \ge 3f+1 \quad \text{is both necessary and sufficient}$$
The $n=3,\,f=1$ case is unsolvable: a traitor commander sends conflicting orders to two loyal lieutenants, and neither can tell who is lying — the majority vote has no honest tiebreaker.

**Signed messages** lift the bound: with unforgeable signatures a traitor can no longer equivocate once its signed message is forwarded, so agreement tolerates any number of traitors in $f+1$ rounds.

### 2. Operational Rules
* **Rule 1 (The 3f+1 wall):** with unsigned messages you cannot tolerate $f$ Byzantine faults with fewer than $3f+1$ nodes — this bound is hard.
* **Rule 2 (Majority over the message tree):** OM($m$) relies on each loyal node majority-voting the values it received through all relay paths.
* **Rule 3 (Signatures change the math):** authenticated signatures defeat equivocation, dropping the requirement toward $2f+1$ reachable (still $f+1$ rounds).
* **Rule 4 (Synchronous assumption):** OM assumes synchronous, authenticated channels; relax these and the model changes (see PBFT for partial synchrony).

### 3. Reference Implementation (Python)
```python
def om(commander, value, lieutenants, faulty, m):
    """OM(m): returns {lieutenant: decided_value}. `faulty` is the set of traitor ids."""
    if m == 0:
        return {lt: value for lt in lieutenants if lt not in faulty}
    decisions = {lt: {} for lt in lieutenants if lt not in faulty}
    for lt in lieutenants:
        relayed = value if commander not in faulty else None     # traitors send arbitrary
        sub = om(lt, relayed, [x for x in lieutenants if x != lt], faulty, m - 1)
        for target, v in sub.items():
            decisions[target][lt] = v
    out = {}
    for lt, msgs in decisions.items():
        msgs[commander] = value if commander not in faulty else None
        out[lt] = majority(list(msgs.values()))                  # Rule 2
    return out

def majority(values):
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)
```
*(OM is exponential in $f$ — it is pedagogical, not production. PBFT makes Byzantine agreement practical.)*

### 4. Agent Execution Prompting Directives
* **When sizing a BFT system:** state the $n \ge 3f+1$ requirement up front and derive $f$ from $n$.
* **When signatures are available:** say so — they cut the node requirement and are the default in modern chains.
* **When citing necessity:** the 3-general / 1-traitor counterexample is the cleanest proof that $n = 3f$ fails; use it.
