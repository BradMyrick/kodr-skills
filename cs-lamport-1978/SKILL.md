---
name: cs-lamport-1978
description: Establishes causal ordering of distributed events via Lamport logical clocks and a process-id total order. Use when implementing happened-before relations, logical timestamps, or distributed event ordering.
version: 1.0.0
title: "Time, Clocks, and the Ordering of Events in a Distributed System"
authors: ["Leslie Lamport"]
venue: "Communications of the ACM, 21(7)"
year: 1978
url: "https://doi.org/10.1145/359545.359563"
related: ["cs-lamport-1982", "cs-lamport-1998"]
---

# Skill: Distributed Causality & Consensus Ordering
## System Reference: Lamport Logical Clocks (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
To establish an ordering of events across decentralized nodes without a shared physical clock, we utilize the **Happens-Before Relation** ($\rightarrow$).

*   If events $a$ and $b$ occur within the same process, and $a$ comes before $b$, then $a \rightarrow b$.
*   If $a$ is the sending of a message by one process and $b$ is the receipt of that same message by another process, then $a \rightarrow b$.
*   If $a \rightarrow b$ and $b \rightarrow c$, then $a \rightarrow c$ (Transitivity).
*   If $a \not\rightarrow b$ and $b \not\rightarrow a$, then $a$ and $b$ are concurrent ($a \parallel b$).

### 2. Operational Rules
Each process $P_i$ maintains a monotonic local counter $L_i$.

*   **Rule 1 (Internal Event):** Before executing an internal event, $P_i$ increments its local clock:
    $$L_i = L_i + 1$$
*   **Rule 2 (Message Passing):**
    *   When sending message $m$, $P_i$ attaches its current clock value: $(m, L_i)$.
    *   Upon receiving $(m, L_{msg})$, the receiving process $P_j$ updates its local clock before delivering the message:
        $$L_j = \max(L_j, L_{msg}) + 1$$

To achieve a **Total Ordering** ($\Rightarrow$) and break ties between concurrent events where $L_i(a) = L_j(b)$, we append the unique process identifier:
$$a \Rightarrow b \iff (L_i(a) < L_j(b)) \lor (L_i(a) == L_j(b) \land i < j)$$

### 3. Reference Implementation (Rust)
```rust
#[derive(Debug, Clone, Eq, PartialEq, Ord, PartialOrd)]
pub struct ProcessId(pub u32);

#[derive(Debug, Clone, Eq, PartialEq)]
pub struct LamportTimestamp {
    pub counter: u64,
    pub process_id: ProcessId,
}

// Implement total ordering
impl Ord for LamportTimestamp {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.counter.cmp(&other.counter)
            .then_with(|| self.process_id.cmp(&other.process_id))
    }
}

impl PartialOrd for LamportTimestamp {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

pub struct DistributedNode {
    pub id: ProcessId,
    pub current_clock: u64,
}

impl DistributedNode {
    pub fn new(id: u32) -> Self {
        Self { id: ProcessId(id), current_clock: 0 }
    }

    pub fn execute_internal_event(&mut self) -> LamportTimestamp {
        self.current_clock += 1;
        LamportTimestamp { counter: self.current_clock, process_id: self.id.clone() }
    }

    pub fn prepare_message<T>(&mut self, payload: T) -> (T, LamportTimestamp) {
        self.current_clock += 1;
        let ts = LamportTimestamp { counter: self.current_clock, process_id: self.id.clone() };
        (payload, ts)
    }

    pub fn receive_message(&mut self, incoming_ts: &LamportTimestamp) {
        self.current_clock = std::cmp::max(self.current_clock, incoming_ts.counter) + 1;
    }
}
```

### 4. Agent Execution Prompting Directives
* **When ordering events without a shared clock:** apply the happens-before rules first; only fall back to the total order (counter, then process-id tiebreak) for concurrent events.
* **When debugging clock skew:** verify the receive rule uses `max(local, msg) + 1` — a missing `+1` or a swapped `max` is the canonical bug.
* **When the global order diverges across nodes:** confirm every node uses the identical process-id tiebreak ($i < j$); inconsistent comparators yield different total orders.
