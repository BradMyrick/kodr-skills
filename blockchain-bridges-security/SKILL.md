---
name: blockchain-bridges-security
description: Cross-chain bridge designs (lock-and-mint, burn-and-mint, liquidity networks) and their trust assumptions, failure modes, and historic exploits. Use when designing or auditing a bridge. NOT for single-chain transfers.
version: 1.0.0
---

# Skill: Bridges & Cross-Chain Security
## System Reference: Trust-Minimized Asset Transfer Between Chains (RFC-Style Engineering Spec)

### 1. Core Model
A bridge moves assets or messages between two chains that cannot verify each other directly. Every bridge rests on some **verification committee / oracle / light client** that attests to events on the source chain so the destination can act. The security reduces to: *how hard is it to lie about the source?*

**Designs:**
| Design | Trust model | Strength |
|---|---|---|
| **Lock-and-mint** | A committee/custodian locks on source, mints a wrapped asset on destination | weakest link = committee |
| **Burn-and-mint** | Burn on source (native), mint on destination | symmetric; still needs attestation |
| **Liquidity pool** | Liquidity providers on both sides swap native assets | capital-inefficient; no wrapped tokens |
| **Light-client / ZK bridge** | Destination verifies source headers (or a ZK proof of them) | strongest; no honest-majority committee |

**Historic lesson:** bridges are the most hacked construct in crypto (Wormhole, Ronin, Nomad, Poly Network — billions lost). The common causes: a multisig key compromise, a buggy signature-verification/merkle handler, or a message that the destination accepted without re-checking.

### 2. Operational Rules
* **Rule 1 (State the trust assumption explicitly):** is security $f$-of-$n$ signers, an honest supermajority, or cryptographic (light-client/ZK)? Say it, and size $n,t$ accordingly (see `blockchain-signatures-threshold`).
* **Rule 2 (Rate-limit + cap):** bound the value a bridge can release per interval; a pause/circuit-breaker must exist and be cheap to trigger.
* **Rule 3 (Re-verify on the destination):** never trust a relayed message blindly — re-check signatures, the Merkle proof, and the source finality before acting.
* **Rule 4 (Respect source finality):** only act after the source transaction is final (probabilistic → wait $z$ confirmations; BFT → after commit).
* **Rule 5 (Isolate keys, rotate, threshold):** committee keys must be threshold-signing, hardware-backed, and rotated; a single stolen key must not move funds.
* **Rule 6 (Prefer trust-minimized designs):** a light-client or ZK bridge removes the committee; use it where the destination can afford the verification cost.

### 3. Reference Implementation (Python — lock-and-mint state machine)
```python
from dataclasses import dataclass, field

@dataclass
class LockMintBridge:
    """Source locks -> committee attests -> destination mints; destination burns -> source releases."""
    locked: dict[str, int] = field(default_factory=dict)      # depositor -> amount locked on source
    minted: dict[str, int] = field(default_factory=dict)      # depositor -> amount minted on dest
    threshold: int = 3
    signers: int = 5
    paused: bool = False
    per_tx_cap: int = 1_000_000

    def lock(self, who: str, amount: int, confirmations: int, required: int):
        if self.paused: raise RuntimeError("bridge paused")
        if amount > self.per_tx_cap: raise ValueError("exceeds per-tx cap")    # Rule 2
        if confirmations < required: raise ValueError("source not final yet")  # Rule 4
        self.locked[who] = self.locked.get(who, 0) + amount

    def attest_and_mint(self, who: str, amount: int, sig_count: int):
        if sig_count < self.threshold:                                         # Rule 1 + Rule 5
            raise ValueError(f"need {self.threshold} sigs, got {sig_count}")
        if self.locked.get(who, 0) < amount: raise ValueError("nothing locked")
        self.locked[who] -= amount
        self.minted[who] = self.minted.get(who, 0) + amount                    # effects before any external call

    def burn_and_release(self, who: str, amount: int, sig_count: int):
        if sig_count < self.threshold: raise ValueError("insufficient sigs")
        if self.minted.get(who, 0) < amount: raise ValueError("not minted")
        self.minted[who] -= amount
        self.locked[who] = self.locked.get(who, 0) + amount                    # release back on source
```

### 4. Agent Execution Directives
* **When auditing a bridge:** map every release path to its trust assumption and its pause; an unpausable, single-sig release path is the exploit.
* **When designing:** default to a rate limit + threshold committee, and migrate to a light-client/ZK verifier when feasible (Rules 2, 6).
* **When citing failures:** Wormhole (signature handling), Nomad (misconfigured root hash), Ronin (key compromise) — each maps to a Rule above.
