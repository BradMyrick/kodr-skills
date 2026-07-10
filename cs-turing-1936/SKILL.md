---
name: cs-turing-1936
description: Defines computation via an abstract automatic machine (a-machine) and proves the undecidability of the halting/Entscheidungsproblem. Use when reasoning about computability, decidability, or building Turing-machine simulators.
version: 1.0.0
title: "On Computable Numbers, with an Application to the Entscheidungsproblem"
authors: ["Alan M. Turing"]
venue: "Proceedings of the London Mathematical Society, s2-42(1)"
year: 1936
url: "https://doi.org/10.1112/plms/s2-42.1.230"
related: ["cs-shannon-1948"]
---

# Skill: Computability & the Turing Machine
## System Reference: The a-Machine / Universal Computer (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
A computation is performed by an **automatic machine (a-machine)**: a finite control in state $q \in Q$ scanning one square of an unbounded tape divided into cells. Each cell holds a symbol from a finite alphabet $\Gamma$ (including a distinguished blank). A single step is governed by the **transition function**:

$$\delta : Q \times \Gamma \;\rightharpoonup\; Q \times \Gamma \times \{L, R, N\}$$

That is, $\delta(q, a) = (q', b, D)$ means: in state $q$ reading symbol $a$, write $b$, enter state $q'$, and move the head in direction $D$ (Left, Right, or None).

* **Configuration** of a machine: $(q, \text{tape contents}, \text{head position})$.
* **Halting:** the machine halts iff $\delta(q, a)$ is undefined for the current $(q, a)$.
* **Computable number:** a real number whose decimal (binary) expansion can be wholly written by some a-machine.

**The Universal Machine $\mathcal{U}$.** There exists a single machine $\mathcal{U}$ which, when given on its tape the **Standard Description (S.D.)** of any machine $\mathcal{M}$ together with $\mathcal{M}$'s input, simulates $\mathcal{M}$ step for step. This is the stored-program principle: program and data share one tape.

**The Entscheidungsproblem.** Turing proves no a-machine can decide, for an arbitrary machine $\mathcal{M}$ and input, whether $\mathcal{M}$ ever halts. Proof by diagonalization: assume a decider $H(\langle\mathcal{M}\rangle, x)$ exists. Construct $\mathcal{D}$ that halts iff $H$ says $\mathcal{D}(\langle\mathcal{D}\rangle)$ does **not** halt. Feeding $\mathcal{D}$ to itself yields a contradiction. Hence the halting problem — and Hilbert's decision problem for first-order logic — is **undecidable**.

### 2. Operational Rules
* **Rule 1 (Finiteness):** both the state set $Q$ and tape alphabet $\Gamma$ must be finite; only $\delta$ determines behavior.
* **Rule 2 (Determinism):** $\delta$ is a partial *function* — at most one action per $(q, a)$. No branching beyond what $\delta$ encodes.
* **Rule 3 (Locality):** a step may inspect only the single scanned square; all state lives in $q$ and the tape.
* **Rule 4 (Universality gate):** to simulate an arbitrary machine, the implementation must treat $\delta$ as *data* (a table on the tape), not as fixed control flow.

### 3. Reference Implementation (Rust)
```rust
use std::collections::HashMap;

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum Move { Left, Right, None }

/// (state, symbol) -> (next_state, write_symbol, move)
type Transition<S, A> = HashMap<(S, A), (S, A, Move)>;

pub struct TuringMachine<S: Eq + std::hash::Hash + Clone, A: Eq + std::hash::Hash + Clone + Copy> {
    tape: HashMap<i64, A>,      // sparse tape; missing => blank
    head: i64,
    state: S,
    blank: A,
    table: Transition<S, A>,
}

impl<S, A> TuringMachine<S, A>
where
    S: Eq + std::hash::Hash + Clone,
    A: Eq + std::hash::Hash + Clone + Copy,
{
    pub fn new(start: S, blank: A, table: Transition<S, A>) -> Self {
        Self { tape: HashMap::new(), head: 0, state: start, blank, table }
    }

    pub fn write(&mut self, sym: A) { self.tape.insert(self.head, sym); }
    pub fn read(&self) -> A { *self.tape.get(&self.head).unwrap_or(&self.blank) }

    /// Execute one step; returns false when the machine halts (no transition).
    pub fn step(&mut self) -> bool {
        let a = self.read();
        match self.table.get(&(self.state.clone(), a)).cloned() {
            Some((q2, b, mv)) => {
                self.tape.insert(self.head, b);
                self.head += match mv { Move::Left => -1, Move::Right => 1, Move::None => 0 };
                self.state = q2;
                true
            }
            None => false, // δ undefined => halt
        }
    }

    /// The universal layer: run until halt or `max_steps` (guards non-termination).
    pub fn run(&mut self, max_steps: u64) -> u64 {
        let mut steps = 0;
        while steps < max_steps && self.step() { steps += 1; }
        steps
    }
}
```

### 4. Agent Execution Prompting Directives
* **When asked "is X computable?":** frame the answer as the existence of a finite $\delta$ whose run produces $X$; do not appeal to physical time or memory limits.
* **When modeling non-termination:** always pair a simulator with a step budget; surface halting as "$\delta$ undefined", never as an exception.
* **When discussing decidability:** state the reduction explicitly (halting $\le$ target problem) before concluding undecidability.
