---
name: blockchain-signatures-threshold
description: Digital signatures for chains — ECDSA/Schnorr/BLS, threshold (t-of-n), multisig, and aggregate schemes. Use when designing key management, threshold signing, or signature aggregation. NOT for key exchange — use cs-diffie-1976.
version: 1.0.0
---

# Skill: Signatures, Threshold & Aggregation
## System Reference: Signature Schemes + Threshold Cryptography (RFC-Style Engineering Spec)

### 1. Core Model
A **digital signature** proves a message came from a known key holder and was not altered. Signer has private key, verifiers use the public key: `σ = Sign(sk, m)`, `Verify(pk, m, σ)`. Chains authenticate every transaction this way.

**Schemes:**
| Scheme | Notes | Aggregation |
|---|---|---|
| **ECDSA** (secp256k1) | Bitcoin/Ethereum default; non-interactive; variable-length | no native agg |
| **Schnorr** | linear, provably secure (ROM), natively **mul­ti­sig & batch** | yes (sum sigs) |
| **BLS** (BLS12-381) | signature is a single group element; **one sig for many** | yes (add points) |

**Threshold (t-of-n).** No single party holds the full key. A committee of $n$ each holds a **key share**; any $t$ of them collaboratively sign, but fewer than $t$ learn nothing. Built on **Shamir secret sharing**: the secret $s$ is the value at $x=0$ of a degree-t-1 polynomial $f$; shares are $f(x_i)$, and any $t$ points reconstruct $f$ (and $s$) via **Lagrange interpolation**, while $< t$ reveal nothing.

**Aggregate/multisig.** Combine many signatures into one to save space and verify in one shot (Schnorr MuSig2, BLS aggregation). Watch the **rogue-key attack**: require proof-of-possession or coefficient binding so a malicious key can't be crafted to cancel honest ones.

### 2. Operational Rules
* **Rule 1 (Threshold defeats single-key compromise):** set $t$ so that compromising $t-1$ signers is still useless; $n \ge 2t-1$ for liveness under $f = n-t$ faults.
* **Rule 2 (Never reconstruct the key):** threshold signing combines *partial* signatures without ever assembling $sk$; reconstruction only at provisioning (if at all).
* **Rule 3 (Bind keys against rogue attacks):** for aggregation, bind each public key to the session (MuSig coefficients / proof-of-possession).
* **Rule 4 (Constant-time + nonce hygiene):** ECDSA/Schnorr are catastrophically broken by nonce reuse or bias (Sony PS3, Android wallet drains); use RFC-6979 deterministic nonces or threshold nonce generation.
* **Rule 5 (Aggregation saves gas):** BLS one-sig-for-many cuts on-chain signature storage (eth2 attester aggregation).

### 3. Reference Implementation (Python — Shamir threshold reconstruction)
```python
# Pure-math illustration of the t-of-n reconstruction that underlies threshold sigs.
# Real threshold signing combines partial *signatures* over the curve, not the secret.
from typing import List, Tuple

P = 2**521 - 1   # large prime for the field (illustrative)

def eval_poly(coeffs: List[int], x: int, p: int = P) -> int:
    """Horner evaluation of f(x) mod p."""
    acc = 0
    for c in reversed(coeffs):
        acc = (acc * x + c) % p
    return acc

def make_shares(secret: int, t: int, n: int, p: int = P) -> List[Tuple[int, int]]:
    import random
    coeffs = [secret] + [random.randrange(1, p) for _ in range(t - 1)]   # degree t-1
    return [(x, eval_poly(coeffs, x, p)) for x in range(1, n + 1)]        # shares (x, f(x))

def lagrange_reconstruct(shares: List[Tuple[int, int]], p: int = P) -> int:
    """Recover f(0) = secret from any t shares via Lagrange interpolation."""
    secret = 0
    for j, (xj, yj) in enumerate(shares):
        num = den = 1
        for m, (xm, _) in enumerate(shares):
            if m == j: continue
            num = (num * (-xm)) % p
            den = (den * (xj - xm)) % p
        secret = (secret + yj * num * pow(den, -1, p)) % p
    return secret % p

if __name__ == "__main__":
    secret = 0x1234_5678_9abc
    shares = make_shares(secret, t=3, n=5)
    assert lagrange_reconstruct(shares[:3]) == secret     # any t=3 recover it
    assert lagrange_reconstruct(shares[:2]) != secret     # t-1=2 reveal nothing
```

### 4. Agent Execution Directives
* **When sizing a signing committee:** derive $t$ and $n$ from the threat model (Rule 1); quote $n \ge 2t-1$ for liveness.
* **When aggregating signatures:** mitigate the rogue-key attack (Rule 3) before claiming a size win.
* **When auditing nonce handling:** reject any RNG-derived or reused nonce (Rule 4) — it is an immediate key-recovery bug.
