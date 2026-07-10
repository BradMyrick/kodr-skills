---
name: security-software
description: Software security practices for systems written in Rust and Go. Covers supply chain auditing, dependency hygiene, threat modeling, secret management, secure coding patterns, SAST/DAST tooling, and CI security hardening. Use when reviewing code for vulnerabilities, setting up security tooling, or designing secure systems.
version: 1.0.0
---

# Software Security

## Rust-Specific Safety

Rust eliminates entire vulnerability classes by design, but unsafe code, dependency chains, and logic bugs still require attention.

### Minimize `unsafe`
- Wrap all `unsafe` blocks in a safe abstraction with documented invariants.
- Use `#[forbid(unsafe_code)]` at the crate root for libraries that have no business using unsafe.
- Audit any crate that exposes `unsafe` in its public API.

### Integer Overflow
Debug builds panic on overflow; release builds wrap silently. Be explicit:
```rust
// Prefer checked arithmetic in sensitive paths
let result = a.checked_add(b).ok_or(AgentError::Overflow)?;

// Or use saturating/wrapping when that's the intended semantic
let len = buf.len().saturating_add(header_size);
```

### Avoiding Timing Attacks
Use constant-time comparison for secrets (tokens, hashes):
```rust
use subtle::ConstantTimeEq;
let ok = expected_mac.ct_eq(&received_mac).into();
```

## Supply Chain Security

### cargo-audit
Run against the RustSec advisory database:
```sh
cargo install cargo-audit
cargo audit
```
In CI:
```yaml
- name: Security audit
  run: cargo audit --deny warnings
```

### cargo-deny
Enforces license policy, duplicate crates, and banned crates:
```sh
cargo install cargo-deny
cargo deny check
```

`deny.toml` example:
```toml
[advisories]
db-path = "~/.cargo/advisory-db"
db-urls = ["https://github.com/rustsec/advisory-db"]
vulnerability = "deny"
unmaintained = "warn"

[licenses]
allow = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"]
deny = ["GPL-3.0"]

[bans]
multiple-versions = "warn"
```

### Lock File Hygiene
- Commit `Cargo.lock` in binaries/applications; do not commit it in libraries.
- Pin critical security-sensitive crates (`openssl`, `ring`, `rustls`) to reviewed versions.
- Enable Dependabot for automatic lock file PRs.

## Secret Management

- **Never hardcode secrets** in source, even in `.env` files committed to the repo.
- Load secrets from environment variables or a secrets manager (Vault, AWS SSM, Doppler).
- Rotate secrets immediately if accidentally exposed in git history (`git filter-repo`, then rotate).

```rust
// Correct: read from env at startup
let api_key = std::env::var("API_KEY")
    .context("API_KEY env var not set")?;
```

- Use `zeroize` to clear sensitive memory after use:
```rust
use zeroize::Zeroizing;
let secret: Zeroizing<Vec<u8>> = Zeroizing::new(load_key()?);
// Automatically zeroed on drop
```

## Input Validation and Parsing

- Parse, don't validate — use strong types to represent only valid states.
- Never construct SQL, shell commands, or OS paths by string concatenation with user input.
- Limit input sizes before processing to prevent DoS.

```rust
const MAX_PAYLOAD: usize = 1 << 20; // 1 MiB
if input.len() > MAX_PAYLOAD {
    return Err(AgentError::PayloadTooLarge);
}
```

## Network Security

- Default to TLS — use `rustls` (pure Rust, no OpenSSL dependency).
- Pin certificates in high-assurance services.
- Bind to `127.0.0.1` in local-only services; never `0.0.0.0` unless explicitly required.
- Rate-limit all public-facing endpoints.

## SAST / DAST Tooling

| Tool | Purpose | How to Run |
|---|---|---|
| `cargo-audit` | Known CVEs in dependencies | `cargo audit` |
| `cargo-deny` | License + supply chain policy | `cargo deny check` |
| `cargo-semver-checks` | API compatibility | `cargo semver-checks` |
| CodeQL | Deep semantic SAST | GitHub Actions `github/codeql-action` |
| `trivy` | Container + dependency scanning | `trivy fs .` |
| `semgrep` | Custom rule SAST | `semgrep --config=auto` |

### CodeQL in CI
```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: rust

- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v3
```

## Threat Modeling Checklist
Before shipping a service, validate:
- [ ] All external inputs are validated/parsed before use
- [ ] Authentication and authorization enforced at the API boundary
- [ ] Secrets never logged or returned in error responses
- [ ] Dependency audit passes clean
- [ ] TLS enforced for all network connections
- [ ] Resource limits (memory, CPU, connections) are bounded
- [ ] Audit log of privileged operations exists
