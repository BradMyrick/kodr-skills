---
name: blockchain-state-machines
description: State-machine replication and authenticated state storage — Merkle-Patricia trie, sparse Merkle trees, and state/account roots. Use when designing chain state, proofs, or replay. NOT for the consensus that orders state transitions.
version: 1.0.0
---

# Skill: State Machines & Authenticated State
## System Reference: Replicated State Machine + Authenticated Storage (RFC-Style Engineering Spec)

### 1. Core Model
A blockchain is a **replicated state machine**: every honest node, starting from the genesis state and applying the same ordered sequence of transactions, ends at the same state. The consensus orders transactions; **deterministic execution** guarantees convergence. Non-determinism (floating point, RNG, wall-clock) is forbidden.

**Authenticated state.** To prove a node isn't lying about state, the entire state is committed to a **state root**:

* **Merkle-Patricia Trie (MPT)** — Ethereum's structure: keys are nibbles; nodes are hashed; supports efficient insert/delete/update of `(key → value)` with $O(\log)$ proof of any account/storage slot. Combines a trie (path compression via Patricia) with Merkle hashing.
* **Sparse Merkle Tree (SMT)** — a Merkle tree of depth = key-bit-length, where most leaves are the default (empty); gives $O(\text{keylen})$ inclusion/non-inclusion proofs and is simpler to implement.

The **state root** $R$ is the hash of the trie root; a block header carries $R$, so anyone with the header + a proof can verify a slice of state without trusting the node.

### 2. Operational Rules
* **Rule 1 (Execution is deterministic):** forbid floats, wall-clock, and entropy in transaction execution; source randomness from the block header (e.g. a VRF or commit-reveal).
* **Rule 2 (State root in the header):** every block commits to its post-state root; mismatch with recomputed root = invalid block.
* **Rule 3 (Proofs for light clients):** inclusion (and, for SMTs, non-inclusion) is provable with a hash path — don't require the whole state.
* **Rule 4 (Pruning vs archival):** full nodes may prune old state but must keep the root history; archival nodes keep everything — choose role explicitly.
* **Rule 5 (Reorg-safe state):** state transitions must be reversible up to finality; keep a recent snapshot per height for fast re-execution after a reorg.

### 3. Reference Implementation (Python — Sparse Merkle Tree)
```python
import hashlib

def H(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

EMPTY = H(b"")            # default leaf hash
DEPTH = 256               # one level per key bit

class SparseMerkleTree:
    def __init__(self, depth: int = DEPTH):
        self.depth = depth
        # store only non-default nodes; everything else is the cached subtree default
        self.nodes: dict[str, bytes] = {}
        self._defaults = self._default_hashes(depth)

    def _default_hashes(self, depth: int) -> list[bytes]:
        d = [EMPTY]
        for _ in range(depth):
            d.append(H(d[-1] + d[-1]))     # a subtree of all-empty hashes to this level
        return d

    def _key_bits(self, key: bytes) -> list[int]:
        return [(b >> (7 - i)) & 1 for b in key for i in range(8)][:self.depth]

    def set(self, key: bytes, value: bytes):
        idx = int.from_bytes(key, "big") % (1 << self.depth)
        node = H(value)
        self.nodes[(self.depth, idx)] = node          # leaf
        for level in range(self.depth - 1, -1, -1):
            idx //= 2
            left  = self.nodes.get((level + 1, idx * 2),     self._defaults[level + 1])
            right = self.nodes.get((level + 1, idx * 2 + 1), self._defaults[level + 1])
            self.nodes[(level, idx)] = H(left + right)

    def root(self) -> bytes:
        return self.nodes.get((0, 0), self._defaults[0])

if __name__ == "__main__":
    t = SparseMerkleTree(depth=16)         # small depth for the demo
    t.set(b"\x01", b"alice:100")
    t.set(b"\x09", b"bob:250")
    print("state root:", t.root().hex()[:16], "...")
```

### 4. Agent Execution Directives
* **When designing execution:** audit every opcode/host function for non-determinism (Rule 1); it breaks consensus convergence silently.
* **When proving state to light clients:** return the Merle path against the committed state root (Rule 3), not a full dump.
* **When choosing MPT vs SMT:** MPT for Ethereum-compatible keyed maps; SMT for simpler non-inclusion proofs and easier caching.
