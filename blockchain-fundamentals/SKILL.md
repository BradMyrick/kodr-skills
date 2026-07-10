---
name: blockchain-fundamentals
description: Cryptographic data structures for chains — hashes, Merkle trees, commitments, and the UTXO-vs-account accounting model. Use when reasoning about inclusion/absence proofs, commitment schemes, or choosing an accounting model. NOT for consensus — use blockchain-consensus.
version: 1.0.0
---

# Skill: Blockchain Fundamentals — Hashes, Merkle & Accounting Models
## System Reference: Cryptographic Append-Only Data Structures (RFC-Style Engineering Spec)

### 1. Core Model
A blockchain is an append-only log of **blocks**, each committing to the previous one by hash and to its transactions via a **Merkle root**. Hashing gives tamper-evidence: changing any byte changes hashes all the way up the chain.

**Hash function.** A one-way compression $H: \{0,1\}^* \to \{0,1\}^n$ (e.g. SHA-256, Keccak-256) that is preimage-, second-preimage-, and collision-resistant. The chain links blocks by $H_k = H(\text{header}_k \| H_{k-1})$.

**Merkle tree.** A binary hash tree whose **root** commits to a set of leaves; membership of leaf $i$ is proven by $\log_2 n$ sibling hashes (an **inclusion proof**). Tampering any leaf changes the root.

**Commitment.** Bind to a value now, reveal later: $C = H(r \| m)$ with secret nonce $r$ (hides $m$, later verifiable).

**Accounting models.**
* **UTXO** (Bitcoin): each tx consumes prior outputs and creates new ones; parallelizable, no global mutable state, balance = sum of unspent outputs.
* **Account** (Ethereum): global state maps `address → {nonce, balance, code, storage}`; a tx mutates one account; natural for smart contracts.

### 2. Operational Rules
* **Rule 1 (Hash-then-link):** every block commits to its parent's hash; rewriting history re-hashes the whole suffix.
* **Rule 2 (Merkle for cheap verification):** light clients verify inclusion with $O(\log n)$ hashes, not the whole block.
* **Rule 3 (Commit before reveal):** never let a counterparty adapt their value to yours; commit with a random nonce.
* **Rule 4 (Model choice shapes everything):** UTXO favors parallelism and simple scripts; accounts favor rich stateful contracts — pick deliberately, it's near-impossible to switch later.

### 3. Reference Implementation (Python)
```python
import hashlib

def H(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

def merkle_root(leaves: list[bytes]) -> bytes:
    if not leaves:
        return H(b"")
    level = [H(l) for l in leaves]
    while len(level) > 1:
        if len(level) % 2:                       # duplicate last if odd
            level.append(level[-1])
        level = [H(level[i] + level[i+1]) for i in range(0, len(level), 2)]
    return level[0]

def merkle_proof(leaves: list[bytes], index: int) -> list[bytes]:
    """Sibling hashes along the path from leaf[index] to the root."""
    level = [H(l) for l in leaves]
    proof = []
    idx = index
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sib = idx ^ 1                            # sibling is the other child
        proof.append(level[sib])
        level = [H(level[i] + level[i+1]) for i in range(0, len(level), 2)]
        idx //= 2
    return proof

def verify_proof(leaf: bytes, index: int, proof: list[bytes], root: bytes) -> bool:
    h = H(leaf)
    idx = index
    for sib in proof:
        h = H(sib + h) if idx % 2 else H(h + sib)   # order by index parity
        idx //= 2
    return h == root

if __name__ == "__main__":
    txs = [b"tx0", b"tx1", b"tx2", b"tx3"]
    root = merkle_root(txs)
    p = merkle_proof(txs, 2)
    assert verify_proof(txs[2], 2, p, root)
```

### 4. Agent Execution Directives
* **When proving membership:** emit the $\log_2 n$ sibling path; never reserialize the whole block to verify a leaf.
* **When choosing the accounting model:** state up front (UTXO vs account) and justify with parallelism/statefulness needs.
* **When committing:** always mix in a secret nonce to prevent chosen-value attacks (Rule 3).
