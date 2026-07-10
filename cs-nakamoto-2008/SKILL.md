---
name: cs-nakamoto-2008
description: Solves electronic double-spend via a proof-of-work blockchain whose longest chain encodes consensus without a trusted authority. Use when designing/auditing blockchains, proof of work, or double-spend resistance.
version: 1.0.0
title: "Bitcoin: A Peer-to-Peer Electronic Cash System"
authors: ["Satoshi Nakamoto"]
venue: "Self-published whitepaper (cryptography mailing list)"
year: 2008
url: "https://bitcoin.org/bitcoin.pdf"
related: ["cs-lamport-1982"]
---

# Skill: The Proof-of-Work Blockchain & Trustless Consensus
## System Reference: Nakamoto Consensus (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
A network of nodes agrees on a public transaction history (the **chain**) with no trusted party. Double-spending is prevented not by a central ledger but by making history computationally expensive to rewrite.

**Block structure.** Each block links to its predecessor by hash:
$$H_k = \operatorname{SHA256d}(\text{prev\_hash}_k \,\|\, \text{MerkleRoot}(\text{txs}) \,\|\, \text{timestamp} \,\|\, \text{bits} \,\|\, \text{nonce})$$

**Proof of work.** A miner extends the chain by finding a nonce whose block hash falls below a difficulty target $T$:
$$H_k < T$$
The expected work to find such a nonce is $\propto 2^{256}/T$; periodic retargeting keeps the mean block interval near 10 minutes.

**Longest-(most-work)-chain rule.** Honest nodes extend the chain with the greatest cumulative work. To reverse a transaction buried $z$ blocks deep, an attacker controlling hash-power fraction $q$ (honest $p = 1-q$) must catch up. From the paper's gambler's-ruin/Poisson analysis, success is $1$ if $q \ge p$, otherwise:
$$P(q, z) = 1 - \sum_{k=0}^{z} \frac{\lambda^{k} e^{-\lambda}}{k!}\left(1 - \left(\tfrac{q}{p}\right)^{z-k}\right), \qquad \lambda = z\,\frac{q}{p}$$
This drops exponentially in $z$ — the basis for "confirmations."

### 2. Operational Rules
* **Rule 1 (Most-work chain wins):** nodes adopt the chain with greatest cumulative work, breaking ties by first-seen.
* **Rule 2 (Independent verification):** every node validates every block and transaction before relaying — trust is minimized, never assumed.
* **Rule 3 (Difficulty retarget):** the target adjusts periodically so mean inter-block time stays constant despite hash-power drift.
* **Rule 4 (Confirmations):** treat a payment as settled only after $z$ confirmations; pick $z$ so $P(q,z)$ is negligible for the attacker share you must defend against.
* **Rule 5 (Majority honesty):** the security argument requires honest miners to collectively hold the majority of hash power ($p > q$).

### 3. Reference Implementation (Python)
```python
import hashlib, struct, time

def sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

class Block:
    def __init__(self, prev_hash: bytes, txs: list, bits: int, nonce: int = 0):
        self.prev_hash, self.txs, self.bits, self.nonce = prev_hash, txs, bits, nonce
        self.timestamp = int(time.time())

    def merkle_root(self) -> bytes:
        level = [sha256d(tx) for tx in self.txs] or [b"\x00" * 32]
        while len(level) > 1:
            nxt = [sha256d(level[i] + level[i+1]) for i in range(0, len(level)-1, 2)]
            if len(level) % 2:
                nxt.append(sha256d(level[-1] + level[-1]))
            level = nxt
        return level[0]

    def header(self) -> bytes:
        return (self.prev_hash + self.merkle_root()
                + struct.pack("<I", self.bits) + struct.pack("<Q", self.timestamp)
                + struct.pack("<Q", self.nonce))

    def hash(self) -> int:
        return int.from_bytes(sha256d(self.header()), "little")

def target_from_bits(bits: int) -> int:
    exp = bits >> 24
    coeff = bits & 0x007fffff
    return coeff * (1 << (8 * (exp - 3)))

def mine(block: "Block") -> int:
    target = target_from_bits(block.bits)          # Rule 3: target set by difficulty
    while block.hash() >= target:                   # Rule: H < target
        block.nonce += 1
    return block.nonce

def cumulative_work(chain: list) -> int:            # Rule 1: compare total work, not length
    return sum(2**256 // max(1, target_from_bits(b.bits)) for b in chain)
```

### 4. Agent Execution Prompting Directives
* **When assessing finality:** quote $P(q,z)$ for the attacker share and depth, not vague "it's confirmed."
* **When comparing forks:** compare cumulative work (sum of $2^{256}/T$ per block), never raw block count.
* **When extending:** never trust a block without re-verifying its PoW and all transactions (Rule 2) — relay-then-forget is an attack vector.
