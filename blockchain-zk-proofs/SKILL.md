---
name: blockchain-zk-proofs
description: Zero-knowledge proof systems — zk-SNARKs, zk-STARKs, PLONK — and when to apply them for privacy, rollups, or verifiable computation. Use when designing privacy, validity rollups, or proving computation off-chain. NOT for ordinary signatures — use blockchain-signatures-threshold.
version: 1.0.0
---

# Skill: Zero-Knowledge Proofs
## System Reference: Prover/Verifier + Commitments + Soundness (RFC-Style Engineering Spec)

### 1. Core Model
A **zero-knowledge proof** lets a **prover** convince a **verifier** that a statement is true, revealing nothing but its truth. Three guarantees:
* **Completeness:** true statements are provable.
* **Soundness:** false statements are provable only with negligible probability.
* **Zero-knowledge:** the verifier learns nothing but validity.

A proof argues knowledge of a **witness** $w$ (e.g. a secret key) satisfying a relation $R(x, w)$ for public **statement** $x$, without exposing $w$.

**Families:**
| System | Trusted setup | Proof size | Verifier | Post-quantum | Notes |
|---|---|---|---|---|---|
| **Groth16** | per-circuit | tiny (~200 B) | ms | no | smallest proofs |
| **PLONK** | universal, updatable | small | fast | no | one setup, many circuits |
| **STARK** | none (transparent) | larger (kB) | fast (hashes) | yes | arithmetization via AIR |

**The mechanism (Schnorr, interactive → Fiat-Shamir):** the prover commits to randomness, the verifier issues a challenge, the prover responds; the verifier checks an algebraic relation. **Fiat-Shamir** makes it non-interactive by deriving the challenge from a hash of the transcript $c = H(\text{commitment} \| x)$ — so the prover can't precompute a lucky challenge.

**Where they're used:** privacy (shielded transfers), **validity rollups** (prove a batch of L2 transactions is valid; L1 verifies one proof), and verifiable off-chain computation.

### 2. Operational Rules
* **Rule 1 (Fiat-Shamir must bind the full transcript):** derive the challenge from *everything* the statement depends on, or a malicious prover adapts the commitment to a weak challenge (the "Fiat-Shamir is broken" class of bugs).
* **Rule 2 (Soundness error ≤ 2^-λ):** choose field/parameters so a cheating prover's success probability is cryptographically negligible.
* **Rule 3 (Verify the verifier's math):** a ZK bug is usually in the circuit/constraint system, not the crypto primitive — audit the arithmetization.
* **Rule 4 (Rollups prove a state transition):** the proof asserts "applying txs to pre-root yields post-root"; the L1 checks the proof + roots, not the txs.
* **Rule 5 (Setup trust):** Groth16/PLONK need a ceremony; STARKs don't — pick by threat model.

### 3. Reference Implementation (Python — Schnorr proof of knowledge via Fiat-Shamir)
```python
import hashlib, secrets

P = 2**445 - 17        # curve25519-ish field order (illustrative); real Schnorr uses a prime-order group
G = 3                  # generator (illustrative)

def modinv(a: int, p: int = P) -> int:
    return pow(a, -1, p)

class Schnorr:
    """Prove knowledge of x such that Y = G^x, without revealing x."""
    def __init__(self, x: int):
        self.x = x
        self.Y = pow(G, x, P)          # public key

    def prove(self) -> tuple[int, int]:
        # Commit: random nonce r (NEVER reuse — see blockchain-signatures-threshold Rule 4)
        r = secrets.randbelow(P)
        R = pow(G, r, P)                                  # commitment
        # Challenge via Fiat-Shamir (Rule 1: bind R and Y)
        c = int.from_bytes(hashlib.sha256(f"{R},{self.Y}".encode()).digest(), "big") % P
        # Response: s = r + c*x
        s = (r + c * self.x) % P
        return (R, s)

    @staticmethod
    def verify(Y: int, R: int, s: int) -> bool:
        c = int.from_bytes(hashlib.sha256(f"{R},{Y}".encode()).digest(), "big") % P
        # G^s == R * Y^c  (completeness & soundness)
        return pow(G, s, P) == (R * pow(Y, c, P)) % P

if __name__ == "__main__":
    sk = Schnorr(secrets.randbelow(P))
    R, s = sk.prove()
    assert Schnorr.verify(sk.Y, R, s)
```

### 4. Agent Execution Directives
* **When implementing Fiat-Shamir:** hash the entire transcript (commitments + statement + public inputs); a partial transcript is a forgery vector (Rule 1).
* **When building a rollup:** the proof proves `apply(txs, pre_root) == post_root`; never let the verifier trust unproven txs.
* **When choosing a system:** tiny proofs + trusted setup → Groth16/PLONK; transparent + post-quantum → STARK.
