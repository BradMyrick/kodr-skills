---
name: cs-cook-1971
description: Defines NP-completeness and proves SAT is NP-complete, establishing the P vs NP question and the polynomial-reduction methodology. Use when proving NP-hardness, writing reductions, or reasoning about complexity classes.
version: 1.0.0
title: "The Complexity of Theorem-Proving Procedures"
authors: ["Stephen A. Cook"]
venue: "STOC 1971"
year: 1971
url: "https://doi.org/10.1145/800157.805047"
related: ["cs-turing-1936"]
---

# Skill: NP-Completeness & Polynomial Reductions (Cook-Levin)
## System Reference: SAT as the Universal NP Problem (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Cook (and independently Levin) defined the class of problems whose **solutions can be verified in polynomial time** ($\mathbf{NP}$) and proved the first **NP-complete** problem: Boolean satisfiability (SAT).

**Reduction.** $A \le_p B$ means $A$ reduces to $B$ in polynomial time: there is a poly-time computable $f$ with $x \in A \iff f(x) \in B$. If $B \in \mathbf{P}$ then so is $A$.

**NP-complete.** $L$ is NP-complete iff (1) $L \in \mathbf{NP}$, and (2) every $L' \in \mathbf{NP}$ reduces to $L$:
$$\forall L' \in \mathbf{NP},\; L' \le_p L$$

**Cook-Levin theorem.** SAT is NP-complete. Proof idea: encode the polynomial-time computation of a nondeterministic Turing machine $M$ on input $x$ as a Boolean formula $\varphi_{M,x}$ that is satisfiable **iff** $M$ accepts $x$. The tableau of $M$'s configurations across time steps becomes a Boolean array; local consistency (transition function, head movement, tape copying) is expressed as clauses. Thus every NP problem reduces to SAT.

**The central question.** Whether every problem with efficiently checkable solutions also has efficiently findable solutions is exactly:
$$\mathbf{P} \stackrel{?}{=} \mathbf{NP}$$
A single NP-complete problem in $\mathbf{P}$ would collapse them.

### 2. Operational Rules
* **Rule 1 (Direction of reduction):** to prove $X$ NP-hard, reduce a **known** NP-complete problem **to** $X$ ($\text{NPC} \le_p X$), not the reverse.
* **Rule 2 (Polynomial bound):** the reduction and its output size must be polynomial; exponential blowups do not transfer hardness.
* **Rule 3 (Membership):** NP-hard $\land$ in-NP $=$ NP-complete; confirm both separately.
* **Rule 4 (Verification first):** a candidate certificate for an NP problem must check in polynomial time — that is the defining trait.

### 3. Reference Implementation (Python)
```python
# Reduction demo: 3-SAT  <=p  INDEPENDENT-SET
# Given a 3-CNF formula, build a graph with an independent set of size k
# iff the formula is satisfiable -- proving INDEPENDENT-SET is NP-hard.

def reduce_3sat_to_independent_set(clauses, num_vars):
    """Each clause -> a triangle of 3 literal vertices; edges link contradicting literals."""
    nodes, edges, groups = [], set(), []
    vid = 0
    for clause in clauses:
        group = []
        for lit in clause:
            nodes.append(lit)
            group.append(vid)
            vid += 1
        groups.append(group)
        a, b, c = group
        edges |= {(a, b), (b, c), (a, c)}        # triangle: choose at most one literal per clause
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if nodes[i] == -nodes[j]:             # x and ~x cannot both be true
                edges.add((i, j))
    k = len(clauses)                              # need one true literal per clause
    return nodes, sorted(edges), k

# An INDEPENDENT-SET solver run on this graph yields a satisfying assignment;
# hence INDEPENDENT-SET is NP-hard (3-SAT <=p IS, and 3-SAT is NP-complete).
```

### 4. Agent Execution Prompting Directives
* **When proving hardness:** name the source NP-complete problem and show the poly-time mapping both ways ($x \in A \iff f(x) \in B$).
* **When a problem feels intractable:** reduce SAT / 3-SAT / Hamiltonian / etc. **to** it, rather than searching for an algorithm.
* **When citing:** Cook (1971) is the original; the Cook–Levin theorem credits Levin's independent 1973 proof.
