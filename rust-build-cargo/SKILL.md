---
name: rust-build-cargo
description: Structures Cargo workspaces, features, release profiles, and dependency hygiene (cargo-deny/audit). Use when setting up a workspace, feature flags, release/Cargo profiles, or auditing the supply chain. NOT for application logic.
version: 1.0.0
---

# Skill: Cargo, Workspaces & Dependency Hygiene
## System Reference: Workspace + Features + Profiles + Supply-Chain Audits (RFC-Style Engineering Spec)

### 1. Core Model
A **workspace** groups related crates that share a target dir, lockfile, and dependency versions. **Features** are compile-time toggles (`#[cfg(feature = "...")]`) that add optional code/dependencies. **Profiles** control codegen (`dev`/`release`/`bench`). **Supply-chain hygiene** keeps dependencies free of known vulnerabilities, unwanted licenses, and duplicate/banned crates.

A well-structured repo: one workspace, each crate focused, features additive and orthogonal, a locked `Cargo.lock` committed for binaries, and CI that runs `cargo fmt --check`, `clippy -D warnings`, `cargo audit`, and `cargo deny check`.

### 2. Operational Rules
* **Rule 1 (One workspace):** group crates under a root `Cargo.toml` with `[workspace] members = [...]`; shared deps in `[workspace.dependencies]`, referenced as `dep = { workspace = true }`.
* **Rule 2 (Features are additive):** features only *add* code/capabilities, never remove; two features must compose without conflict (no mutually-exclusive features).
* **Rule 3 (Commit Cargo.lock for bins; not required for libs):** reproducible binaries need the lockfile; libraries leave it to downstream.
* **Rule 4 (Tighten the release profile):** `lto = "thin"`, `codegen-units = 1`, `opt-level = 3`, `strip = true`; `panic = "abort"` only if you accept no unwinding.
* **Rule 5 (Audit the supply chain):** `cargo deny check` (advisories, licenses, bans/duplicates) and `cargo audit` in CI; fail the build on a known CVE.
* **Rule 6 (Pin and minimize):** prefer fewer, well-maintained deps; avoid `git` deps in published crates; use `cargo tree`/`cargo bloat` to spot bloat.
* **Rule 7 (CI gates):** `fmt --check`, `clippy -- -D warnings`, `test`, `deny check`, `audit` must all pass on every PR.

### 3. Reference Configuration
```toml
# Cargo.toml (workspace root)
[workspace]
resolver = "2"
members  = ["crates/core", "crates/cli", "crates/server"]

[workspace.package]
version = "0.3.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[workspace.dependencies]
serde   = { version = "1.0", features = ["derive"] }
tokio   = { version = "1", features = ["rt-multi-thread", "macros", "signal"] }
anyhow  = "1"

# crates/server/Cargo.toml
# [package]
# name = "server"
# version.workspace = true
# edition.workspace = true
# [dependencies]
# serde = { workspace = true }
# tokio = { workspace = true }

[profile.release]
lto           = "thin"      # Rule 4: whole-program optimization
codegen-units = 1           #            better optimization, slower compile
opt-level     = 3
strip         = "symbols"
# panic       = "abort"     # uncomment only if no unwinding is needed

[profile.bench]
debug = true                # so profilers (perf/flamegraph) show symbols
```

```toml
# deny.toml — run with `cargo deny check` (Rule 5)
[advisories]
db-urls = ["https://github.com/rustsec/advisory-db"]
yanked  = "deny"

[licenses]
allow = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Unicode-DFS-2016"]
confidence-threshold = 0.93

[bans]
multiple-versions = "warn"
deny = [{ name = "openssl", wrappers = [] }]   # prefer rustls; ban direct openssl
```

### 4. Agent Execution Directives
* **When scaffolding a repo:** one workspace, `[workspace.dependencies]` for shared versions, `resolver = "2"` (feature unification).
* **When adding a feature flag:** keep it additive (Rule 2); gate optional deps with `dep:foo` to avoid auto-enabling them.
* **In CI:** wire `fmt --check` + `clippy -D warnings` + `test` + `deny check` + `audit` as required checks; see `devops-github-workflows`.
