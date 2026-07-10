---
name: dist-partitioning
description: Data partitioning and sharding — consistent hashing, virtual nodes, resharding, and hotspot handling. Use when distributing data across nodes, rebalancing, or fixing hot keys. NOT for replication of a shard — use dist-replication.
version: 1.0.0
---

# Skill: Partitioning & Sharding
## System Reference: Consistent Hashing + Virtual Nodes + Rebalancing (RFC-Style Engineering Spec)

### 1. Core Model
Sharding splits a dataset across $N$ nodes so each owns a slice. The hard part is **rebalancing**: adding/removing a node should move little data, not rehash everything.

**Consistent hashing** places nodes and keys on a **hash ring**; a key is owned by the first node clockwise from its position. Adding a node only takes the keys in its arc — $O(1/N)$ of the keys move — instead of $O(1)$ rehash of everything. Removing a node hands its arc to its neighbor. This is why Dynamo/Cassandra/scaling caches use it.

**Virtual nodes (vnodes).** Each physical node maps to many (100–1000) virtual points on the ring. This balances load when nodes have unequal capacity and spreads a failing node's load across many survivors rather than dumping it on one neighbor.

**Hotspots.** A skewed key distribution (a celebrity's row, a time bucket) overwhelms one shard. Mitigate with **salting** (prepend a random shard-bucket) or **range-splitting**. Choose the **partition key** so writes spread evenly and co-located reads stay together.

**Resharding** must be online: dual-write to old+new during migration, or use a log (CDC) to backfill, then cut over with a brief write freeze.

### 2. Operational Rules
* **Rule 1 (Consistent hashing for elastic clusters):** use a ring + vnodes so add/remove moves $O(1/N)$ data, not a full rehash.
* **Rule 2 (Vnodes for balance):** 100–1000 vnodes per physical node; more = better balance, more routing memory.
* **Rule 3 (Choose the partition key for spread + locality):** even write spread, but keep co-read data on one shard; never shard on a monotonic/sequential key alone (creates a single hot shard).
* **Rule 4 (Online resharding):** migrate via dual-write + CDC backfill, never a stop-the-world rehash on large data.
* **Rule 5 (Replication is orthogonal):** partitioning decides *where*; replication decides *how many copies* (`dist-replication`).

### 3. Reference Implementation (Python — consistent hash ring with vnodes)
```python
import hashlib
from dataclasses import dataclass, field

def H(s: str) -> int:
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")

@dataclass
class Ring:
    vnodes: int = 150
    # position -> node id
    ring: list[tuple[int, str]] = field(default_factory=list)

    def add(self, node: str):
        for v in range(self.vnodes):
            self.ring.append((H(f"{node}#{v}"), node))
        self.ring.sort()

    def remove(self, node: str):
        self.ring = [(pos, n) for pos, n in self.ring if n != node]

    def owner(self, key: str) -> str:
        import bisect
        if not self.ring:
            raise RuntimeError("empty ring")
        pos = H(key)
        # first node at or after pos on the ring (wrapping)
        idx = bisect.bisect_left(self.ring, (pos,))
        if idx == len(self.ring):
            idx = 0
        return self.ring[idx][1]

if __name__ == "__main__":
    r = Ring()
    for n in ["A", "B", "C"]: r.add(n)
    owners = {r.owner(f"k{i}") for i in range(10_000)}      # spreads across A/B/C
    assert owners == {"A", "B", "C"}
    r.add("D")                                               # adds D; moves ~1/4 of keys, not all
    print("after adding D, owners:", {r.owner(f"k{i}") for i in range(10_000)})
```

### 4. Agent Execution Directives
* **When sharding:** default to consistent hashing + vnodes; only use range/hashing when you have a specific locality reason.
* **When a key is hot:** salt or split it; never let one shard absorb a celebrity row.
* **When rebalancing:** plan an online migration (dual-write/CDC) with a measurable cutover, not a rehash outage.
