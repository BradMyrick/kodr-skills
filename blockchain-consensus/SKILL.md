---
name: blockchain-consensus
description: Selects a consensus mechanism — PoW, PoS, BFT, or leader-based — with finality and fork-choice trade-offs. Use when choosing or comparing consensus for a chain; theory in cs-nakamoto-2008 / cs-castro-1999 / cs-lamport-1998 / cs-ongaro-2014. NOT for a specific L1's ops — use blockchain-avalanche.
version: 1.0.0
---

# Skill: Consensus Selection for Blockchains
## System Reference: PoW / PoS / BFT / Leader + Finality + Fork-Choice (RFC-Style Engineering Spec)

### 1. Core Model
A chain's consensus decides the canonical block order and provides two guarantees:
* **Safety (finality):** two honest nodes never finalize conflicting blocks.
* **Liveness:** new transactions keep getting finalized.

The four families trade these off against decentralization and performance:

| Family | Sybil resistance | Finality | Fault model | Throughput | Reference |
|---|---|---|---|---|---|
| **PoW** (Nakamoto) | compute | probabilistic ($P(q,z)$) | < 50% hash power | low | `cs-nakamoto-2008` |
| **PoS** (BFT-style) | stake | instant/economic | < 1/3 stake Byzantine | medium | Tendermint/Casper |
| **BFT leader** | permissioned/quorum | instant | < 1/3 Byzantine | medium-high | `cs-castro-1999` |
| **Leader / Raft** | permissioned | instant | < 1/2 crash | high (no Byzantine) | `cs-ongaro-2014` |

**Finality type.** *Probabilistic* (PoW): a block is "final" with probability →1 as depth $z$ grows (`cs-nakamoto-2008`'s $P(q,z)$). *Absolute* (BFT/PoS): a block is final the moment $\ge 2f+1$ commit, never reverted.

**Fork choice.** The rule honest nodes use to pick the canonical chain: *longest/most-work* (PoW), *LMD-GHOST* (Ethereum — follow the heaviest subtree), *latest committed* (BFT — whatever 2f+1 finalized).

**Accountability & nothing-at-stake.** PoS must punish equivocation (slashing) so signing two conflicting histories costs stake; without slashing, PoS has "nothing at stake" (free to sign every fork).

### 2. Operational Rules
* **Rule 1 (Match finality to the use case):** payments/settlement need fast/absolute finality → BFT/PoS; censorship-resistant open networks may accept probabilistic finality → PoW.
* **Rule 2 (Quorum bounds):** BFT needs $n \ge 3f+1$ (`cs-castro-1999`, `cs-lamport-1982`); leader-based crash-only needs $n \ge 2f+1$ (`cs-ongaro-2014`).
* **Rule 3 (Slashing for PoS):** every equivocation must be slashable, or the stake is meaningless.
* **Rule 4 (Fork choice is a safety lever):** pick a fork-choice rule whose safety you can prove under your fault model (most-work under < 50%; GHOST under network delay assumptions).
* **Rule 5 (Throughput ≠ decentralization):** raising block size/rate centralizes validators (bandwidth/hardware); state the decentralization target before tuning throughput.

### 3. Reference Implementation (Python — finality & fork-choice helpers)
```python
# (a) PoW probabilistic finality (see cs-nakamoto-2008 for the full Poisson formula).
def attacker_success_prob(q: float, z: int) -> float:
    """P(attacker catches up from z blocks behind), honest share p = 1-q."""
    import math
    p = 1 - q
    if q >= p:
        return 1.0
    lam = z * q / p
    return 1 - sum((lam**k * math.exp(-lam) / math.factorial(k))
                   * (1 - (q / p)**(z - k)) for k in range(z + 1))

# (b) LMD-GHOST: follow the heaviest subtree (Ethereum fork choice).
def lmd_ghost(children: dict, votes: dict, genesis: str) -> str:
    """children: block -> [child blocks]; votes: validator -> block id (latest)."""
    weight = {b: 0 for b in children}
    for target in votes.values():
        node = target
        while node is not None:                      # each vote weights its ancestor chain
            weight[node] = weight.get(node, 0) + 1
            node = parents.get(node)
    head = genesis
    while children.get(head):                        # descend toward the heaviest child
        head = max(children[head], key=lambda c: weight.get(c, 0))
    return head

parents = {}  # populated by the chain; block -> parent
```

### 4. Agent Execution Directives
* **When asked "which consensus?":** return the family table + the fault model + finality type, then pick (Rule 1) — never recommend a mechanism without stating the trust assumption.
* **When designing PoS:** specify the slashing condition and the economic security ($\text{stake slashed} \ge \text{gain from attack}$).
* **When citing:** probabilistic finality → `cs-nakamoto-2008`; BFT bounds → `cs-castro-1999`/`cs-lamport-1982`; crash-fault → `cs-ongaro-2014`/`cs-lamport-1998`.
