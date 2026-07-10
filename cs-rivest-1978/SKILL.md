---
name: cs-rivest-1978
description: Provides public-key encryption and digital signatures from the hardness of integer factorization (RSA). Use when implementing or auditing public-key crypto, signatures, or reasoning about the factoring assumption and padding requirements.
version: 1.0.0
title: "A Method for Obtaining Digital Signatures and Public-Key Cryptosystems"
authors: ["Ronald L. Rivest", "Adi Shamir", "Leonard Adleman"]
venue: "Communications of the ACM, 21(2)"
year: 1978
url: "https://doi.org/10.1145/359340.359342"
related: ["cs-diffie-1976"]
---

# Skill: RSA — Factoring-Based Public-Key Cryptography
## System Reference: The RSA Trapdoor Permutation (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
RSA exploits that finding $e$-th roots modulo $n = pq$ is easy with the factorization but believed hard without it.

**Key generation.**
1. Choose two large random primes $p, q$; set $n = pq$.
2. Compute Euler's totient $\varphi(n) = (p-1)(q-1)$ (equivalently Carmichael $\lambda(n)$).
3. Pick public exponent $e$ with $\gcd(e, \varphi(n)) = 1$ (commonly $e = 65537$).
4. Compute private exponent $d \equiv e^{-1} \pmod{\varphi(n)}$.
5. Publish $(n, e)$; keep $d$ (and $p, q$) secret.

**Encryption / Decryption** (textbook RSA, message $m \in [0, n)$):
$$c = m^e \bmod n, \qquad m = c^d \bmod n$$
Correctness follows from Euler's theorem: $m^{ed} \equiv m \pmod n$ when $\gcd(m, n) = 1$.

**Digital signatures** (sign by "decrypting" the hash):
$$\sigma = H(m)^d \bmod n, \qquad \text{verify: } \sigma^e \bmod n \stackrel{?}{=} H(m)$$

**Security.** Recovering $d$ from $(n, e)$ requires factoring $n$; the **factoring assumption** (no polynomial-time factoring algorithm) underpins RSA. Crucially, **textbook RSA is not secure** — it is deterministic and malleable, so real systems wrap it in randomized padding (OAEP for encryption, PSS for signatures).

### 2. Operational Rules
* **Rule 1 (Never use textbook RSA):** encryption MUST use OAEP (or RSA-KEM); signatures MUST use PSS. Raw $m^e \bmod n$ leaks and is forgeable.
* **Rule 2 (Size the modulus):** use $\ge 2048$-bit $n$ (3072+ for long-term); $p, q$ comparable size with large $|p-q|$.
* **Rule 3 (Public exponent):** prefer $e = 65537$ (Fermat F4) — small, odd, efficient, resists small-exponent attacks.
* **Rule 4 (Hash before signing):** sign $H(m)$, never $m$ directly; choose a collision-resistant hash.
* **Rule 5 (Constant-time):** decryption/signing must run in constant time; blinded exponentiation defends against timing and fault attacks.

### 3. Reference Implementation (Python, textbook + padding hooks)
```python
from math import gcd

def keygen(p: int, q: int, e: int = 65537):
    n = p * q
    phi = (p - 1) * (q - 1)
    assert gcd(e, phi) == 1, "e must be coprime to phi(n)"
    d = pow(e, -1, phi)                       # private exponent (keep p, q, d secret)
    return (n, e), (n, d)

def encrypt(pub, m: int) -> int:
    n, e = pub
    assert 0 <= m < n
    # WARNING: textbook -- production must use OAEP / RSA-KEM (Rule 1)
    return pow(m, e, n)

def decrypt(priv, c: int) -> int:
    n, d = priv
    return pow(c, d, n)

def sign(priv, digest: int) -> int:           # Rule 4: sign a hash, not the message
    n, d = priv
    return pow(digest, d, n)

def verify(pub, digest: int, sigma: int) -> bool:   # production: RSA-PSS
    n, e = pub
    return pow(sigma, e, n) == digest
```

### 4. Agent Execution Prompting Directives
* **When auditing:** reject any `m**e % n` or unpadded RSA in code — it is textbook and broken; require OAEP/PSS.
* **When sizing:** match modulus to threat lifetime (2048-bit ≈ 112-bit security, 3072-bit ≈ 128-bit).
* **When asked about quantum risk:** yes — Shor's algorithm factors $n$ in polynomial time; plan migration to lattice/KEM schemes for the post-quantum era.
