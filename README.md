# kodr-skills

A structured **source of truth** for a coding agent across Rust, blockchain,
distributed systems, and distributed AI. Each skill is a directory with a
`SKILL.md` whose frontmatter declares its identity and whose body is an
RFC-style spec (model, rules, reference implementation, directives).

`AGENTS.md` (in this repo) is the **always-on** layer — a short constitution
plus a **skill router** that points the agent at the right skill. Wire it into
opencode via `instructions` in `~/.config/opencode/opencode.json`. Skills are
then loaded on-demand by the `skill` tool, routed by `description`.

## Naming convention

Directories use **`<category>-<specific>`** and the frontmatter `name` matches
the directory exactly (lowercase, hyphens): e.g. dir `rust-async-tokio`,
`name: rust-async-tokio`. The category prefix is the routing family.

```
skills/
├── rust-async-tokio/SKILL.md
├── dist-consensus-engineering/SKILL.md
└── ai-collective-comms/SKILL.md
```

```yaml
---
name: ai-collective-comms
description: Collective communication primitives ... Use when quantifying the communication cost of distributed training.
version: 1.0.0
---
```

### Categories

| Category | Domain | # |
|---|---|---:|
| `rust` | Rust language, tooling, and the async/concurrency/memory model | 10 |
| `blockchain` | Blockchain consensus, crypto, contracts, and networking | 10 |
| `dist` | Distributed-systems engineering (consistency, replication, transactions) | 11 |
| `ai` | Distributed AI — training & inference parallelism and infrastructure | 12 |
| `cs` | Landmark computer-science papers (theory, ML, distributed systems) | 27 |
| `security` | Secure coding, supply chain, threat modeling | 1 |
| `devops` | CI/CD, release pipelines, GitHub Actions | 1 |
| (other) | Project-specific stacks (TypeSafe AI) | 1 |


## Skills

### `rust`
| Skill | Directory | Summary |
|---|---|---|
| `rust-async-tokio` | `rust-async-tokio` | Designs async/tokio runtimes, tasks, cancellation, backpressure, and LocalSet for non-Sen… |
| `rust-build-cargo` | `rust-build-cargo` | Structures Cargo workspaces, features, release profiles, and dependency hygiene (cargo-de… |
| `rust-capnp` | `rust-capnp` | Cap'n Proto schema design, Rust capnp-rpc bindings, async RPC server/client patterns, zer… |
| `rust-concurrency` | `rust-concurrency` | Designs thread-safe code with Send/Sync, Mutex/RwLock, atomics, memory ordering, and lock… |
| `rust-error-handling` | `rust-error-handling` | Structures error handling with Result, thiserror (library error enums), and anyhow/eyre (… |
| `rust-ownership-lifetimes` | `rust-ownership-lifetimes` | Solves borrow-checker, lifetime, and ownership errors and designs self-referential and ar… |
| `rust-performance` | `rust-performance` | Optimizes Rust by profiling (perf/flamegraph), zero-copy parsing, SIMD, allocator choice,… |
| `rust-testing` | `rust-testing` | Designs Rust test suites across unit, integration, property (proptest), fuzz (cargo-fuzz)… |
| `rust-traits-api` | `rust-traits-api` | Designs ergonomic public APIs via traits, generics, associated types, sealed traits, newt… |
| `rust-unsafe-ffi` | `rust-unsafe-ffi` | Reviews and writes unsafe Rust and FFI with explicit safety contracts, soundness obligati… |

### `blockchain`
| Skill | Directory | Summary |
|---|---|---|
| `blockchain-avalanche` | `blockchain-avalanche` | 2026-current Avalanche development: Layer 1 creation/deploy, Subnet-EVM configs, validato… |
| `blockchain-bridges-security` | `blockchain-bridges-security` | Cross-chain bridge designs (lock-and-mint, burn-and-mint, liquidity networks) and their t… |
| `blockchain-consensus` | `blockchain-consensus` | Selects a consensus mechanism — PoW, PoS, BFT, or leader-based — with finality and fork-c… |
| `blockchain-contract-safety` | `blockchain-contract-safety` | Mandatory safety patterns for smart contracts — reentrancy, integer overflow, checks-effe… |
| `blockchain-fundamentals` | `blockchain-fundamentals` | Cryptographic data structures for chains — hashes, Merkle trees, commitments, and the UTX… |
| `blockchain-gas-mev` | `blockchain-gas-mev` | Fee markets (EIP-1559 base fee + tip), mempool dynamics, and MEV (maximal extractable val… |
| `blockchain-networking` | `blockchain-networking` | P2P networking for chains — gossipsub for block/tx propagation, Kademlia DHT for peer dis… |
| `blockchain-signatures-threshold` | `blockchain-signatures-threshold` | Digital signatures for chains — ECDSA/Schnorr/BLS, threshold (t-of-n), multisig, and aggr… |
| `blockchain-state-machines` | `blockchain-state-machines` | State-machine replication and authenticated state storage — Merkle-Patricia trie, sparse… |
| `blockchain-zk-proofs` | `blockchain-zk-proofs` | Zero-knowledge proof systems — zk-SNARKs, zk-STARKs, PLONK — and when to apply them for p… |

### `dist`
| Skill | Directory | Summary |
|---|---|---|
| `dist-consensus-engineering` | `dist-consensus-engineering` | Decision guide for choosing a consensus protocol — Paxos, Raft, BFT (PBFT/HotStuff), or N… |
| `dist-consistency` | `dist-consistency` | Consistency models (linearizable, serializable, causal, read-your-writes, eventual), CAP/… |
| `dist-crdts` | `dist-crdts` | Conflict-free Replicated Data Types (state- and operation-based) for eventually consisten… |
| `dist-failure-resilience` | `dist-failure-resilience` | Failure detection (heartbeat, Φ-accrual), recovery objectives (RTO/RPO), chaos/fault inje… |
| `dist-idempotency` | `dist-idempotency` | Idempotency keys, deduplication, and exactly-once semantics for retries and message deliv… |
| `dist-load-balancing` | `dist-load-balancing` | Load balancing, backpressure, circuit breakers, rate limiting, and capacity math (Little'… |
| `dist-observability` | `dist-observability` | Observability for distributed systems — metrics, tracing, structured logs (OpenTelemetry)… |
| `dist-partitioning` | `dist-partitioning` | Data partitioning and sharding — consistent hashing, virtual nodes, resharding, and hotsp… |
| `dist-replication` | `dist-replication` | Replication strategies — primary-backup, quorum (NWR), and chain replication — with leade… |
| `dist-transactions` | `dist-transactions` | Distributed transactions and isolation — 2PC/3PC, sagas, the outbox pattern, exactly-once… |
| `dist-transport-security` | `dist-transport-security` | Securing service-to-service channels — mutual TLS (mTLS), the Noise protocol framework, c… |

### `ai`
| Skill | Directory | Summary |
|---|---|---|
| `ai-collective-comms` | `ai-collective-comms` | Collective communication primitives — AllReduce (ring/tree), AllGather, ReduceScatter, Br… |
| `ai-data-parallelism` | `ai-data-parallelism` | Data parallelism — DP, DistributedDataParallel (DDP), gradient bucketing, the parameter-s… |
| `ai-inference-serving` | `ai-inference-serving` | High-throughput LLM inference — PagedAttention/vLLM, continuous batching, KV-cache manage… |
| `ai-memory-analysis` | `ai-memory-analysis` | Memory accounting for large-model training — weights, optimizer state, activations, the K… |
| `ai-mixed-precision` | `ai-mixed-precision` | Mixed-precision training — fp32/bf16/fp16/fp8, dynamic loss scaling, and tensor-core util… |
| `ai-mixture-of-experts` | `ai-mixture-of-experts` | Mixture-of-Experts (MoE) — router/top-k gating, load-balancing auxiliary loss, expert cap… |
| `ai-parallelism-overview` | `ai-parallelism-overview` | The map of distributed-training parallelism — data, tensor, pipeline, sequence, expert, Z… |
| `ai-pipeline-parallelism` | `ai-pipeline-parallelism` | Pipeline parallelism — GPipe vs 1F1B vs interleaved schedules, the pipeline bubble, and m… |
| `ai-resilience-checkpointing` | `ai-resilience-checkpointing` | Resilience for large-scale training — synchronous/async checkpointing, resharding across… |
| `ai-rlhf-infra` | `ai-rlhf-infra` | Infrastructure for RLHF/RLAIF — the actor/critic/reference/reward four-model setup, PPO a… |
| `ai-tensor-parallelism` | `ai-tensor-parallelism` | Tensor & sequence parallelism — Megatron-style column/row weight splitting, the all-reduc… |
| `ai-zero-fsdp` | `ai-zero-fsdp` | Memory sharding for data-parallel training — ZeRO stages 1/2/3 (optimizer state / gradien… |

### `cs`
| Skill | Directory | Summary |
|---|---|---|
| `cs-turing-1936` | `cs-turing-1936` | Defines computation via an abstract automatic machine (a-machine) and proves the undecida… |
| `cs-shannon-1948` | `cs-shannon-1948` | Quantifies information via entropy and mutual information and derives the Shannon-Hartley… |
| `cs-rosenblatt-1958` | `cs-rosenblatt-1958` | Implements the perceptron, a binary linear classifier trained by error-correction (the pe… |
| `cs-cook-1971` | `cs-cook-1971` | Defines NP-completeness and proves SAT is NP-complete, establishing the P vs NP question… |
| `cs-diffie-1976` | `cs-diffie-1976` | Establishes a shared secret between two parties over an insecure channel using exponentia… |
| `cs-lamport-1978` | `cs-lamport-1978` | Establishes causal ordering of distributed events via Lamport logical clocks and a proces… |
| `cs-rivest-1978` | `cs-rivest-1978` | Provides public-key encryption and digital signatures from the hardness of integer factor… |
| `cs-lamport-1982` | `cs-lamport-1982` | Solves agreement among loyal generals when some are traitorous, proving n >= 3f+1 replica… |
| `cs-rumelhart-1986` | `cs-rumelhart-1986` | Computes multi-layer neural network weight adjustments, matrix backpropagation gradients,… |
| `cs-hochreiter-1997` | `cs-hochreiter-1997` | Solves the vanishing/exploding gradient problem in recurrent nets with gated memory cells… |
| `cs-lamport-1998` | `cs-lamport-1998` | Achieves distributed consensus among independent nodes via majority quorums across two ba… |
| `cs-page-1998` | `cs-page-1998` | Ranks web pages via the stationary distribution of a damped random walk (PageRank power i… |
| `cs-castro-1999` | `cs-castro-1999` | Makes Byzantine fault tolerance practical for state-machine replication with 3f+1 replica… |
| `cs-nakamoto-2008` | `cs-nakamoto-2008` | Solves electronic double-spend via a proof-of-work blockchain whose longest chain encodes… |
| `cs-krizhevsky-2012` | `cs-krizhevsky-2012` | Classifies images with a deep 8-layer convolutional network (AlexNet) using ReLU activati… |
| `cs-bahdanau-2014` | `cs-bahdanau-2014` | Adds learned alignment between decoder states and encoder hidden states (additive attenti… |
| `cs-kingma-2014` | `cs-kingma-2014` | Optimizes stochastic objectives with adaptive estimates of first and second moments plus… |
| `cs-ongaro-2014` | `cs-ongaro-2014` | Achieves replicated-log consensus via a strong leader with randomized elections and major… |
| `cs-he-2015` | `cs-he-2015` | Enables training of very deep networks via residual (skip) connections that learn identit… |
| `cs-shazeer-2017` | `cs-shazeer-2017` | Introduces the sparsely-gated Mixture-of-Experts layer — a learned router selects top-k e… |
| `cs-vaswani-2017` | `cs-vaswani-2017` | Computes sequence representations via scaled dot-product self-attention and multi-head at… |
| `cs-moritz-2018` | `cs-moritz-2018` | Introduces Ray — a distributed framework unifying task-parallel (stateless) and actor (st… |
| `cs-rajbhandari-2019` | `cs-rajbhandari-2019` | Introduces ZeRO — sharding optimizer state (stage 1), gradients (stage 2), and parameters… |
| `cs-shoeybi-2019` | `cs-shoeybi-2019` | Introduces Megatron-LM tensor parallelism — column/row weight splitting that inserts exac… |
| `cs-brown-2020` | `cs-brown-2020` | Generates text from a 175B-parameter autoregressive language model conditioned by in-cont… |
| `cs-dao-2022` | `cs-dao-2022` | Introduces FlashAttention — an IO-aware exact attention algorithm that fuses the attentio… |
| `cs-kwon-2023` | `cs-kwon-2023` | Introduces PagedAttention/vLLM — OS-style virtual memory for the KV cache that eliminates… |

### `security`
| Skill | Directory | Summary |
|---|---|---|
| `security-software` | `security-software` | Software security practices for systems written in Rust and Go. Covers supply chain audit… |

### `devops`
| Skill | Directory | Summary |
|---|---|---|
| `devops-github-workflows` | `devops-github-workflows` | GitHub Actions CI/CD workflows for Rust projects. Covers build matrices, caching, fmt/cli… |

### Other project stacks
| Skill | Directory | Summary |
|---|---|---|
| `typesafe-ai` | `typesafe-ai` | Build AI-powered software with TypeSafe: small units of AI intelligence you can use lik… |

## Usage

**Any harness:** see [INSTALL.md](INSTALL.md) — a paste-ready prompt that has
your agent wire this repo into whatever instruction/skill mechanism it supports.

**opencode:** point `opencode.json` at this directory and load `AGENTS.md` as an instruction:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["~/.config/opencode/skills/AGENTS.md"],
  "skills": { "paths": ["~/.config/opencode/skills"] }
}
```

## Adding a skill

1. Pick the category (or introduce a new one-word prefix).
2. Create `<category>-<specific>/SKILL.md` (dir name == `name`).
3. Frontmatter: `name` (hyphen, == dir), a `description` that says **what** and
   **when** (front-load trigger keywords; add a `NOT for` gate if it overlaps a
   sibling), and `version`.
4. Body: Core Model → Operational Rules → Reference Implementation → Agent
   Directives (code must compile / type-check).
5. Add a routing line to `AGENTS.md` and a row will appear here automatically.

> `cs-*` skills also carry citation frontmatter (`title`/`authors`/`venue`/
> `year`/`url`) as source-of-truth metadata.
