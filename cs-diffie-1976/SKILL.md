---
name: cs-diffie-1976
description: Establishes a shared secret between two parties over an insecure channel using exponentiation modulo a prime (Diffie-Hellman key exchange). Use when designing key agreement, forward secrecy, or reasoning about the discrete-logarithm assumption.
version: 1.0.0
title: "New Directions in Cryptography"
authors: ["Whitfield Diffie", "Martin E. Hellman"]
venue: "IEEE Transactions on Information Theory, 22(6)"
year: 1976
url: "https://doi.org/10.1109/TIT.1976.1055638"
related: ["cs-rivest-1978"]
---

# Skill: Diffie-Hellman Key Exchange & Public-Key Cryptography
## System Reference: Discrete-Logarithm Key Agreement (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Two parties, Alice and Bob, with no prior shared secret and an eavesdropper reading every message, derive a **shared key**. They publish a large prime $p$ and a generator $g$ of a large subgroup of $\mathbb{Z}_p^*$.

1. Alice picks secret $a \in [1, p{-}2]$, sends $A = g^a \bmod p$.
2. Bob picks secret $b \in [1, p{-}2]$, sends $B = g^b \bmod p$.
3. Shared secret:
$$K = (g^b)^a = g^{ab} = (g^a)^b \equiv B^a \equiv A^b \pmod p$$

An eavesdropper sees $g, p, A, B$ and must recover $a$ or $b$ — the **Discrete Logarithm Problem (DLP)**: given $g$ and $g^a \bmod p$, find $a$. No polynomial-time algorithm is known for DLP over well-chosen groups; this asymmetry is the entire security foundation.

**Forward secrecy.** If $a, b$ are ephemeral (fresh each session), compromising long-term keys later cannot recover past $K$ — the property that makes (EC)DHE the standard for TLS key establishment.

### 2. Operational Rules
* **Rule 1 (Group choice):** use a safe prime $p = 2q+1$ (or a standardized group); never a random prime — small-subgroup attacks recover exponents.
* **Rule 2 (Validate peer values):** reject $A$ or $B$ outside $[2, p{-}2]$ to avoid small-subgroup / invalid-element attacks.
* **Rule 3 (Ephemeral for secrecy):** use fresh exponents per session for forward secrecy (DHE); long-term-static DH is replayable.
* **Rule 4 (Authenticate the exchange):** DH alone is unauthenticated and vulnerable to man-in-the-middle; sign the transcript or bind it to identities.
* **Rule 5 (Move to ECC):** elliptic-curve DH (ECDH on Curve25519/P-256) gives equivalent security at ~256-bit keys with far better performance.

### 3. Reference Implementation (Python)
```python
import secrets

def dh_exchange(p: int, g: int):
    """Returns (private, public) for one party."""
    a = secrets.randbelow(p - 2) + 1
    return a, pow(g, a, p)

def shared_secret(priv: int, peer_pub: int, p: int) -> int:
    if not (2 <= peer_pub <= p - 2):                 # Rule 2: validate peer value
        raise ValueError("invalid public value")
    return pow(peer_pub, priv, p)

# Tiny demo only. In production use a vetted safe prime from RFC 7919,
# or ECDH on Curve25519 -- never hand-rolled primes:
p, g = 23, 5
a, A = dh_exchange(p, g); b, B = dh_exchange(p, g)
assert shared_secret(a, B, p) == shared_secret(b, A, p)   # both derive g^ab
```

### 4. Agent Execution Prompting Directives
* **When reviewing a DH deployment:** check the group (safe prime / standard curve), peer-value validation, and authentication — the trio that closes the classic MITM / subgroup holes.
* **When asked "is it secure?":** it reduces to DLP; state the assumed hardness and key sizes (≥2048-bit finite-field DH, or ≥256-bit ECC).
* **When designing protocols:** prefer ephemeral ECDHE for forward secrecy, and bind the transcript to long-term identity keys.
