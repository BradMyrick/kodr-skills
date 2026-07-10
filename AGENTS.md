# AGENTS.md — Kodr Skills Constitution & Skill Router

This file is **always-on context** for every coding agent. It defines the
non-negotiable engineering principles and routes you to the right specialist
skill. Load a skill via the `skill` tool **before** designing or implementing
in its domain.

## Core Principles (non-negotiable)

1. **Correctness before performance.** A fast wrong answer is a bug. Prove the
   invariant first; optimize a measured hot path second.
2. **Security is fail-closed.** Default to deny; never log or commit secrets;
   validate all untrusted input; use constant-time comparison for secrets.
3. **Name the governing invariant before deciding.** Every distributed choice
   is a trade-off — CAP, quorum intersection, the roofline, `n ≥ 3f+1`, the
   factoring / discrete-log assumption. State which one applies before proposing.
4. **Assume failure and adversaries.** Design for the crash, partition,
   Byzantine actor, OOM, or node-loss case first — not the happy path.
5. **Idempotency & exactly-once by default** for any side-effectful or retried
   operation (keys, dedup, outbox).
6. **Verify before you finish.** Compile; run tests, lints, and fuzzers; never
   assert correctness you did not actually check.
7. **Simplicity over cleverness.** Prefer the obviously-correct design; reach
   for subtlety only with a measured reason.

## Skill Router

Match the task to a skill. When several could apply, pick the **most specific**;
first match wins. If no skill fits an architecture decision, fall back to the
relevant `cs-*` foundational paper, then to the Core Principles.

### Rust — safety first
- ownership / borrow / lifetime errors → `rust-ownership-lifetimes`
- `unsafe`, FFI, soundness review → `rust-unsafe-ffi` (**mandatory before approving any `unsafe`**)
- Send/Sync, locks, atomics, memory ordering, lock-free → `rust-concurrency`
- async / tokio / runtime / cancellation / backpressure → `rust-async-tokio`
- Result / thiserror / anyhow / error context → `rust-error-handling`
- tests / property tests / fuzz / benchmarks → `rust-testing`
- trait design / generics / type-state / API ergonomics → `rust-traits-api`
- profiling / zero-copy / SIMD / allocators → `rust-performance`
- Cargo / workspace / features / cargo-deny → `rust-build-cargo`
- Cap'n Proto / `.capnp` / capnp-rpc → `rust-capnp`

### Blockchain — assume adversaries
- **ANY smart-contract work → `blockchain-contract-safety` FIRST** (reentrancy, overflow, checks-effects-interactions, access control)
- choosing a consensus mechanism → `blockchain-consensus`; theory in `cs-nakamoto-2008` (PoW), `cs-castro-1999`/`cs-lamport-1982` (BFT), `cs-lamport-1998`/`cs-ongaro-2014` (crash-fault)
- keys / signatures / threshold / aggregate (ECDSA/Schnorr/BLS) → `blockchain-signatures-threshold`
- hashes / Merkle / commitments / UTXO-vs-account → `blockchain-fundamentals`
- state machines / Merkle-Patricia trie / state roots → `blockchain-state-machines`
- gas / fees / EIP-1559 / MEV / mempool → `blockchain-gas-mev`
- p2p / gossip / discovery → `blockchain-networking`
- bridges / cross-chain → `blockchain-bridges-security`
- ZK proofs (SNARK/STARK/PLONK) → `blockchain-zk-proofs`
- Avalanche L1 / Subnet-EVM / Warp → `blockchain-avalanche`

### Distributed systems — name the consistency model
- consistency models / CAP-PACELC / clocks / ordering → `dist-consistency`
- choosing Paxos / Raft / BFT / PoW for a system → `dist-consensus-engineering`
- replication / quorum (NWR) / chain → `dist-replication`
- sharding / consistent hashing / resharding → `dist-partitioning`
- 2PC / saga / outbox / exactly-once / isolation → `dist-transactions`
- failure detection / Φ-accrual / RTO-RPO / chaos → `dist-failure-resilience`
- CRDTs / eventual merge → `dist-crdts`
- load balancing / backpressure / circuit breakers → `dist-load-balancing`
- idempotency / dedup → `dist-idempotency`
- mTLS / Noise / secure channels → `dist-transport-security`
- metrics / tracing / SLI-SLO / USE-RED → `dist-observability`

### Distributed AI — communication is the bottleneck
- **START HERE** for any training/inference parallelism → `ai-parallelism-overview` (pick data/model/pipeline/tensor/expert/ZeRO, then go deep)
- collective comms / AllReduce / NCCL / roofline / overlap → `ai-collective-comms` (**quantify before proposing**)
- data-parallel / DDP / parameter server / gossip / async → `ai-data-parallelism`
- tensor / sequence parallelism (Megatron) → `ai-tensor-parallelism`
- pipeline parallelism (GPipe / 1F1B / bubbles) → `ai-pipeline-parallelism`
- ZeRO / FSDP sharding → `ai-zero-fsdp`
- MoE routing / expert parallelism → `ai-mixture-of-experts`
- activation memory / recomputation / offloading → `ai-memory-analysis`
- bf16 / fp8 / loss scaling / tensor cores → `ai-mixed-precision`
- checkpoint / resume / fault tolerance at scale → `ai-resilience-checkpointing`
- inference serving (vLLM / PagedAttention / KV-cache / spec decode) → `ai-inference-serving`
- RLHF / PPO / GRPO infra → `ai-rlhf-infra`
- origin/proof of any claim → the matching `cs-*` paper (`cs-shoeybi-2019`, `cs-rajbhandari-2019`, `cs-kwon-2023`, `cs-dao-2022`, `cs-shazeer-2017`, `cs-moritz-2018`)

### Cross-cutting
- security review / hardening / supply chain → `security-software`
- CI/CD / GitHub Actions / releases → `devops-github-workflows`

## Routing discipline
- If two skills match, load the **more specific** one; still tied → load both and reconcile.
- Cite the governing invariant in your reasoning (e.g. `n ≥ 3f+1`, `C = W·log₂(1+S/N)`, the roofline number).
- Every `cs-*` skill is both reference and proof — prefer it over intuition for foundational claims.
