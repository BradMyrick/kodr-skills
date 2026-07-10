---
name: dist-replication
description: Replication strategies — primary-backup, quorum (NWR), and chain replication — with leader election and replica placement. Use when designing data replication, read/write quorums, or failover. NOT for the consensus that elects the leader — use dist-consensus-engineering.
version: 1.0.0
---

# Skill: Replication Strategies
## System Reference: Primary-Backup / Quorum / Chain Replication (RFC-Style Engineering Spec)

### 1. Core Model
Replication stores data on multiple nodes for durability and availability. Three archetypes:

**Primary-backup (leader-follower).** One **primary** accepts writes and forwards them to backups; reads may hit any replica (eventual) or just the primary (strong). Simple, but the primary is a bottleneck and a single point of failover complexity.

**Quorum replication (NWR).** Data is stored on $N$ replicas; each write reaches $W$ nodes, each read contacts $R$ nodes. **Quorum intersection** guarantees strong reads if:
$$R + W > N \quad \text{and} \quad W > N/2$$
(any read quorum overlaps the last write quorum in at least one up-to-date replica). Typical: $N=3, W=2, R=2$; tune for read-heavy ($R$ low) or write-heavy.

**Chain replication.** Replicas form a chain: head receives writes, they flow tail-ward, the tail serves reads and acks. Linearizable by construction; failover replaces head/tail. Used by Azure Cosmos/Cassandra-style systems and (conceptually) by many BFT chains.

**Leader election** is a separate concern (see `dist-consensus-engineering`): replication *uses* a leader, consensus *chooses* it.

### 2. Operational Rules
* **Rule 1 (Quorum intersection ⇒ strong reads):** enforce $R+W>N$ and $W>N/2$ for linearizable reads; document if you relax it for throughput.
* **Rule 2 (Ack on durable copies):** a write is durable only once $W$ replicas have fsync'd it; acking before durability loses data on failover.
* **Rule 3 (Failover must be fenced):** ensure a stale primary cannot accept writes after a new one is elected — use epoch/term fencing (`cs-ongaro-2014`, `cs-lamport-1998`).
* **Rule 4 (Anti-entropy for lag):** run background merkle/anti-entropy so slow replicas catch up; lag must be bounded and observable.
* **Rule 5 (Placement across failures):** spread replicas across racks/availability zones so a single failure can't take down all copies.

### 3. Reference Implementation (Python — quorum write/read)
```python
import random

class QuorumStore:
    """N replicas, W write quorum, R read quorum. Demonstrates R+W>N strong reads."""
    def __init__(self, n=3, w=2, r=2):
        assert w > n / 2 and r + w > n, "violates quorum intersection"
        self.n, self.w, self.r = n, w, r
        self.replicas: list[dict] = [{} for _ in range(n)]   # each replica: key -> (value, version)

    def write(self, key, value):
        version = max((self.replicas[i].get(key, (None, -1))[1] for i in range(self.n)), default=-1) + 1
        contacted = random.sample(range(self.n), self.w)     # write to W replicas (Rule 2: would fsync)
        for i in contacted:
            self.replicas[i][key] = (value, version)
        return version

    def read(self, key):
        contacted = random.sample(range(self.n), self.r)     # read from R replicas
        best = max((self.replicas[i].get(key, (None, -1)) for i in contacted), key=lambda t: t[1])
        return best[0]

if __name__ == "__main__":
    s = QuorumStore(n=3, w=2, r=2)
    s.write("k", "v1")
    # Even if we read a stale replica, the quorum intersection returns the latest (Rule 1)
    print("read:", s.read("k"))
```

### 4. Agent Execution Directives
* **When sizing a store:** set $(N, W, R)$ from the durability/latency/consistency target and prove $R+W>N$ (Rule 1).
* **When designing failover:** add epoch/term fencing so split-brain primaries can't corrupt data (Rule 3).
* **When choosing the topology:** primary-backup for simplicity, chain for linearizability, quorum for tunable trade-offs.
