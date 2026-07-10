---
name: dist-transport-security
description: Securing service-to-service channels — mutual TLS (mTLS), the Noise protocol framework, certificate/PKI rotation, AEAD, and cert pinning. Use when designing authenticated, encrypted RPC between services. NOT for end-user auth — focus on transport between nodes.
version: 1.0.0
---

# Skill: Transport Security for Services
## System Reference: mTLS / Noise / AEAD / PKI Rotation (RFC-Style Engineering Spec)

### 1. Core Model
Internal services must authenticate each other and encrypt the wire. The standard is **mutual TLS (mTLS)**: both sides present and verify X.509 certificates issued by a private CA; the TLS handshake gives **confidentiality** (encryption), **integrity** (AEAD), and **mutual authentication** (each side proves its identity via its cert). With mTLS, service identity is the cert's SPIFFE/SAN — no shared passwords on the wire.

**Noise Protocol Framework** is the modern alternative (used by WireGuard, libp2p, WhatsApp): a small set of composable handshake patterns that give the same properties with far less complexity than TLS, ideal for peer-to-peer and constrained links.

**AEAD** (AES-GCM, ChaCha20-Poly1305) gives encryption + authentication in one primitive; never use unauthenticated encryption (AES-CTR/CBC without a MAC) — it's malleable.

**Rotation & PKI.** Certificates expire and keys rotate (compromise, cadence). A healthy system issues **short-lived certs** (hours–days) via an automated CA (SPIFFE/SPIRE, cert-manager, step-ca) and rotates them without restarts. Long-lived certs with manual rotation are an outage-and-compromise risk.

**Cert pinning.** Defeat CA compromise/MitM for high-value clients by pinning an expected key/hash and rejecting mismatches — at the cost of rotation complexity.

### 2. Operational Rules
* **Rule 1 (Mutual auth, not just server auth):** internal services must verify each other — mTLS or Noise with mutual identity, never one-way TLS with a password.
* **Rule 2 (AEAD always):** authenticated encryption (AES-GCM/ChaCha20-Poly1305); never unauthenticated modes.
* **Rule 3 (Short-lived, auto-rotated certs):** issue hours/days-lived certs from an automated CA; rotate without downtime.
* **Rule 4 (Identity from the cert, not the network):** authorize by the verified identity (SPIFFE ID/SAN), not by IP — IPs are spoofable/shared.
* **Rule 5 (Nonce uniqueness is critical):** AEAD with a reused (key, nonce) is catastrophic; use a counter or random nonce with a per-key limit.
* **Rule 6 (Encrypt + authenticate at the boundary):** terminate TLS at the service (or a sidecar) and authorize there; don't rely on "the network is trusted."

### 3. Reference Implementation (Python — cert fingerprint verification + AEAD nonce rule)
```python
import hashlib

def cert_fingerprint(der_cert: bytes) -> str:
    """SHA-256 fingerprint of a certificate's public key (for pinning)."""
    return hashlib.sha256(der_cert).hexdigest()

def verify_pinned(actual: bytes, pinned_hashes: set[str]) -> bool:
    """Cert pinning: accept only if the presented cert matches a known pin (Rule 6)."""
    return cert_fingerprint(actual) in pinned_hashes

class AEADEncoder:
    """Illustrates the (key, nonce) uniqueness rule — the heart of AEAD safety."""
    def __init__(self, key: bytes):
        self.key = key
        self.counter = 0
    def next_nonce(self) -> bytes:
        # Rule 5: a monotonic counter guarantees no (key, nonce) reuse for a given key
        self.counter += 1
        return self.counter.to_bytes(12, "big")
    def seal(self, plaintext: bytes, aad: bytes = b"") -> tuple[bytes, bytes]:
        nonce = self.next_nonce()
        # real: ciphertext = AEAD.encrypt(self.key, nonce, plaintext, aad)
        ciphertext = plaintext[::-1]                       # placeholder for the AEAD call
        return nonce, ciphertext
    @staticmethod
    def never_reuse_proof():
        # Reusing (key, nonce) across two plaintexts reveals XOR of plaintexts AND breaks auth.
        # The counter makes this impossible within one key's lifetime.
        return True

if __name__ == "__main__":
    enc = AEADEncoder(b"k" * 32)
    n1, c1 = enc.seal(b"hello"); n2, c2 = enc.seal(b"hello")
    assert n1 != n2                                        # nonces never repeat (Rule 5)
```

### 4. Agent Execution Directives
* **For service-to-service:** default to mTLS with short-lived auto-rotated certs and identity-based authz (Rules 1, 3, 4).
* **When reviewing crypto:** reject unauthenticated modes and any path that could reuse a (key, nonce) (Rules 2, 5).
* **For peer-to-peer/constrained:** prefer Noise over TLS for simplicity.
