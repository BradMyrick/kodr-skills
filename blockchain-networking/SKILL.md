---
name: blockchain-networking
description: P2P networking for chains — gossipsub for block/tx propagation, Kademlia DHT for peer discovery, and message validation. Use when designing chain networking or peer discovery. NOT for a specific L1's data plane — use blockchain-avalanche / oko skills.
version: 1.0.0
---

# Skill: P2P Networking for Blockchains
## System Reference: Gossipsub + DHT Discovery + Validation (RFC-Style Engineering Spec)

### 1. Core Model
A chain network is an **unstructured P2P overlay** in which every node is equal; messages propagate by **gossip**. Two jobs dominate:

**Discovery.** Nodes find peers without a central directory. **Kademlia** is the canonical DHT: each node and key has a 256-bit ID; distance is bitwise XOR $d(x,y) = x \oplus y$; each node keeps $k$-buckets of contacts grouped by distance (powers of two). Lookups converge in $\log n$ hops, and the XOR metric is symmetric and lets queries greedily approach the target.

**Propagation.** Blocks and transactions must reach all nodes quickly without flooding. **Gossipsub** (libp2p) blends:
* a **mesh** of subscribed peers to which a node forwards messages,
* **gossip** of message-IDs (IHAVE/WANT) to peers outside the mesh,
* a **score** that penalizes misbehaving peers (invalid msgs, oversend) and prunes them.

**Validation before relay:** a node validates a block/tx (signature, PoW/consensus, format) *before* forwarding it, so invalid messages don't flood the network — but bounded work per validation prevents DoS amplification.

### 2. Operational Rules
* **Rule 1 (Validate before relay):** never forward a message you haven't checked; unchecked relay is an amplification DoS vector.
* **Rule 2 (Bound fan-out):** gossip to a mesh of degree $D$ (typically ~6–12); propagation time is $O(\log n)$ with low overhead.
* **Rule 3 (Score and prune):** drop peers that send invalid/duplicate/excessive messages; a healthy mesh self-cleans.
* **Rule 4 (Discovery is separate from consensus):** DHT finds peers; consensus/orders blocks — don't conflate them.
* **Rule 5 (XOR distance is symmetric):** exploit $d(x,y)=d(y,x)$ so a single lookup directionally converges in $\log n$.

### 3. Reference Implementation (Python — Kademlia distance & gossip fan-out)
```python
import random
from typing import Iterable

def xor_distance(a: int, b: int) -> int:
    return a ^ b                                 # Kademlia metric: symmetric, bucketable

def bucket_index(self_id: int, other_id: int, bits: int = 256) -> int:
    d = xor_distance(self_id, other_id)
    return (bits - d.bit_length()) if d else bits    # which k-bucket the peer lives in

class KBuckets:
    def __init__(self, self_id: int, bits: int = 256, k: int = 16):
        self.self_id, self.bits, self.k = self_id, bits, k
        self.buckets: list[list[int]] = [[] for _ in range(bits + 1)]

    def add(self, peer: int):
        if peer == self.self_id: return
        self.buckets[bucket_index(self.self_id, peer, self.bits)].append(peer)

    def closest(self, target: int, n: int = 16) -> list[int]:
        known = [p for b in self.buckets for p in b]
        return sorted(known, key=lambda p: xor_distance(p, target))[:n]

def gossip_round(peers: Iterable[int], mesh_degree: int, rng=random) -> list[int]:
    """Pick a random mesh subset to forward a message to (Rule 2)."""
    pool = list(peers)
    rng.shuffle(pool)
    return pool[:mesh_degree]

if __name__ == "__main__":
    me = 0xabc
    kb = KBuckets(me)
    for p in [0x111, 0x122, 0xfff, 0xabc ^ 0x1, 0xabc ^ 0x8000]:
        kb.add(p)
    print("closest to target:", [hex(p) for p in kb.closest(0xabc ^ 0x1)])
```

### 4. Agent Execution Directives
* **When designing propagation:** set mesh degree for $O(\log n)$ spread; never flood to all peers.
* **When wiring discovery:** use Kademlia/XOR for $\log n$ lookups; keep it disjoint from the consensus layer.
* **When hardening:** require validation-before-relay and a peer score; an amplification attack is otherwise trivial.
