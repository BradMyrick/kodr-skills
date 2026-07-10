---
name: cs-ongaro-2014
description: Achieves replicated-log consensus via a strong leader with randomized elections and majority log replication, designed for understandability over Paxos. Use when implementing leader-based consensus or crash-fault replicated state machines.
version: 1.0.0
title: "In Search of an Understandable Consensus Algorithm"
authors: ["Diego Ongaro", "John Ousterhout"]
venue: "USENIX Annual Technical Conference 2014"
year: 2014
url: "https://raft.github.io/raft.pdf"
related: ["cs-lamport-1998", "cs-castro-1999"]
---

# Skill: Raft — Understandable Leader-Based Consensus
## System Reference: Leader Election + Log Replication (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Raft decomposes consensus into three orthogonal subproblems, each simpler than Paxos's ballot logic. It tolerates **crash** (not Byzantine) faults over $n$ nodes with majority progress.

**Terms.** Time is divided into monotonically increasing **terms** (integers); each term has at most one elected **leader**. A node is a *follower*, *candidate*, or *leader*.

**1. Leader election.** Followers wait a **randomized election timeout** (e.g. 150–300 ms); if no heartbeat arrives, a follower becomes candidate, increments the term, votes for itself, and requests votes via `RequestVote(term, lastLogIndex, lastLogTerm)`. It wins with a **majority**. Randomization makes split votes rare.

**2. Log replication.** The leader appends the entry and sends `AppendEntries(term, prevLogIndex, prevLogTerm, entries[], leaderCommit)`. A follower appends only if its entry at `prevLogIndex` has term `prevLogTerm` (**Log Matching**); otherwise the leader decrements its `nextIndex` and retries. An entry is **committed** once stored on a majority and covered by the leader's current term.

**3. Safety — Leader Completeness.** Committed entries are never lost. This follows from:
* *Election Restriction:* a candidate's log must be at least as up-to-date as the majority that votes for it (compares last term, then last index).
* *Up-to-date ordering:* $\text{lastLogTerm}_a > \text{lastLogTerm}_b$, or equal terms and $\text{len}_a \ge \text{len}_b$.
* *Commit rule:* a leader commits only entries from its **own** term directly (a famous Raft fix); older entries commit by piggyback when a later term is committed.

### 2. Operational Rules
* **Rule 1 (One leader per term):** terms are the fencing token — stale leaders' RPCs are rejected by term.
* **Rule 2 (Randomized timeouts):** election timers MUST be randomized to avoid perpetual split votes; broadcast time $\ll$ election timeout $\ll$ mean failure interval.
* **Rule 3 (Majority commit):** an entry is committed when on a majority; the leader then advances `leaderCommit` and followers apply up to it.
* **Rule 4 (No over-committing old terms):** a leader commits only its own term's entries directly; older ones commit by piggyback.
* **Rule 5 (Crash, not Byzantine):** Raft assumes honest nodes; it is not BFT (use PBFT/HotStuff for Byzantine settings).

### 3. Reference Implementation (Python)
```python
import random

class Node:
    def __init__(self, id):
        self.id = id
        self.current_term, self.voted_for, self.log = 0, None, []   # log: list[(term, cmd)]
        self.commit_index, self.last_applied = -1, -1
        self.state = "follower"
        self.election_timeout = random.uniform(0.15, 0.30)          # Rule 2

    def last(self):
        return (-1, 0) if not self.log else (len(self.log) - 1, self.log[-1][0])

    def request_vote(self, term, cand_id, last_idx, last_term):
        if term < self.current_term:
            return (self.current_term, False)
        if term > self.current_term:                                 # step down on newer term
            self.current_term, self.voted_for, self.state = term, None, "follower"
        my_idx, my_term = self.last()
        up_to_date = (last_term > my_term) or (last_term == my_term and last_idx >= my_idx)  # Election Restriction
        if self.voted_for in (None, cand_id) and up_to_date:
            self.voted_for = cand_id
            self.election_timeout = random.uniform(0.15, 0.30)
            return (self.current_term, True)
        return (self.current_term, False)

    def append_entries(self, term, prev_idx, prev_term, entries, leader_commit):
        if term < self.current_term:
            return (self.current_term, False)                        # Rule 1
        self.current_term, self.state = term, "follower"             # recognize valid leader
        if prev_idx >= 0:
            if prev_idx >= len(self.log) or self.log[prev_idx][0] != prev_term:
                return (self.current_term, False)                    # Log Matching mismatch
        for i, entry in enumerate(entries):
            idx = prev_idx + 1 + i
            if idx < len(self.log) and self.log[idx][0] != entry[0]:
                self.log = self.log[:idx]                            # truncate conflict
            if idx >= len(self.log):
                self.log.append(entry)
        if leader_commit > self.commit_index:                        # Rule 3
            self.commit_index = min(leader_commit, len(self.log) - 1)
        return (self.current_term, True)
```

### 4. Agent Execution Prompting Directives
* **When implementing:** the most-missed rule is #4 (don't commit prior-term entries directly) — it breaks safety under partition; commit a no-op on leadership instead.
* **When debugging split brain:** check that every RPC path updates `current_term` and steps down — stale terms are the usual culprit.
* **When you need Byzantine tolerance:** Raft is the wrong tool; reach for PBFT or HotStuff.
