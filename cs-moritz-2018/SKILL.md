---
name: cs-moritz-2018
description: Introduces Ray — a distributed framework unifying task-parallel (stateless) and actor (stateful) execution for emerging AI workloads (training, RL, serving). Use when reasoning about cluster orchestration for ML/RL; pairs with ai-parallelism-overview.
version: 1.0.0
title: "Ray: A Distributed Framework for Emerging AI Applications"
authors: ["Philipp Moritz", "Robert Nishihara", "Stephanie Wang", "Alexey Tumanov", "Richard Liaw", "Eric Liang", "Melih Elibol", "Zongheng Yang", "William Paul", "Michael I. Jordan", "Ion Stoica"]
venue: "OSDI 2018 / arXiv:1712.05889"
year: 2018
url: "https://arxiv.org/abs/1712.05889"
related: ["ai-parallelism-overview", "cs-rajbhandari-2019"]
---

# Skill: Ray — Unified Task/Actor Distributed Execution
## System Reference: Stateless Tasks + Stateful Actors + a Global Scheduler (RFC-Style Engineering Spec)

### 1. Core Mathematical Model
Emerging AI workloads (RL especially) mix two patterns the existing systems split across frameworks: **stateless tasks** (pure functions, embarrassingly parallel, like a map) and **stateful actors** (long-lived services holding mutable state, like a model replica or a simulator). Ray unifies both over one cluster with a single programming model.

**Two primitives:**
* A **task** is a stateless function invocation: `f(args) -> result`, scheduled anywhere, retried on failure.
* An **actor** is a stateful process created once; subsequent method calls serialize to it, so its state evolves predictably (a model server, an environment, a parameter shard).

A **distributed scheduler** routes tasks/actors by data locality and resource constraints; a **GCS** (global control store) tracks object lineage so failed tasks can reconstruct their outputs. The **object store** (shared memory per node) moves large arrays by reference, not copy, between tasks co-located on a node — making Python ML pipelines fast.

Ray backs RLlib (RL), Ray Train (distributed training), Ray Serve (inference), and Tune (HP search) under one runtime.

### 2. Operational Rules
* **Rule 1 (Tasks are stateless + idempotent):** schedule anywhere, retry on failure; keep them pure so re-execution is safe.
* **Rule 2 (Actors for state):** use an actor only when you need mutable, ordered state (a model replica, a simulator); over-using actors serializes work.
* **Rule 3 (Locality via the object store):** pass large arrays as object refs; Ray keeps them shared-memory-local when producer/consumer share a node.
* **Rule 4 (Lineage for resilience):** rely on lineage-based reconstruction; don't manually checkpoint intermediate tasks Ray can recompute.
* **Rule 5 (Resource pins):** actors pin resources (GPUs) for their lifetime — size actor pools to the cluster.

### 3. Reference Implementation (Python, Ray-style sketch)
```python
# Ray-like sketch: stateless tasks + a stateful actor.
class ObjectRef: ...                       # opaque handle to a stored object

def task(fn):
    """Decorator: f runs statelessly; result stored in the object store, returned by ref."""
    def wrapper(*args): return ("ref", fn.__name__, args)
    return wrapper

class Actor:
    """Method calls serialize to one stateful instance (ordered, stateful)."""
    def __init__(self, cls): self.cls = cls; self.state = None
    def remote(self, *a):
        if self.state is None: self.state = self.cls(*a)
        return self.state

@task
def train_shard(shard_id, epoch): return f"shard {shard_id} @ {epoch}"

class Model:
    def step(self, grads): return grads  # stateful update

# 8 stateless training tasks (embarrassingly parallel) + 1 stateful model actor.
refs = [train_shard(i, 1) for i in range(8)]
model = Actor(Model).remote()
```

### 4. Agent Execution Directives
* **When orchestrating ML/RL:** model pure parallel steps as tasks, long-lived state as actors; pass big arrays by ref.
* **Cite this paper** as the unified task/actor framework; RLlib/Ray Train/Serve are its library layer.
