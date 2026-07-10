---
name: devops-github-workflows
description: GitHub Actions CI/CD workflows for Rust projects. Covers build matrices, caching, fmt/clippy/test jobs, release artifact publishing, Docker builds, and secret management. Use when writing or debugging .github/workflows/*.yml files.
version: 1.0.0
---

# GitHub Workflows (CI/CD)

## File Location
All workflows live in `.github/workflows/*.yml`. Each file is an independent workflow triggered by `on:` events.

## Standard Rust CI
Runs fmt, clippy, and tests on every push and PR:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

env:
  CARGO_TERM_COLOR: always
  RUST_BACKTRACE: 1

jobs:
  ci:
    name: ${{ matrix.os }} / ${{ matrix.toolchain }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        toolchain: [stable, beta]

    steps:
      - uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ matrix.toolchain }}
          components: rustfmt, clippy

      - name: Cache
        uses: Swatinem/rust-cache@v2
        with:
          shared-key: ${{ matrix.os }}-${{ matrix.toolchain }}

      - run: cargo fmt -- --check
      - run: cargo clippy --all-targets --all-features -- -D warnings
      - run: cargo test --all-features
```

## Release Workflow
Build cross-platform binaries and publish a GitHub release on version tags:

```yaml
name: Release

on:
  push:
    tags: ["v*.*.*"]

jobs:
  build:
    name: Build ${{ matrix.target }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            target: x86_64-unknown-linux-gnu
          - os: macos-latest
            target: aarch64-apple-darwin
          - os: windows-latest
            target: x86_64-pc-windows-msvc

    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}
      - uses: Swatinem/rust-cache@v2

      - name: Build release binary
        run: cargo build --release --target ${{ matrix.target }}

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: binary-${{ matrix.target }}
          path: target/${{ matrix.target }}/release/mybin*

  release:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/
          merge-multiple: true
      - uses: softprops/action-gh-release@v2
        with:
          files: artifacts/**
```

## Caching Best Practices
- Use `Swatinem/rust-cache@v2` — it caches `~/.cargo` registry and `target/` per job.
- Key on OS + toolchain: avoids cache poisoning across matrix legs.
- For monorepos, add `workspaces: "."` to scope the cache correctly.

## Secret Management
- Store secrets in **Settings → Secrets and variables → Actions**.
- Reference in workflows: `${{ secrets.MY_SECRET }}`.
- Never echo secrets; GitHub masks known secret values in logs.
- Use `gh secret set` from the CLI for scripted secret management.

## Dependency Review
Add to PRs to block known-vulnerable dependency upgrades:

```yaml
- uses: actions/dependency-review-action@v4
  with:
    fail-on-severity: moderate
```

## Useful Actions Reference
| Action | Purpose |
|---|---|
| `actions/checkout@v4` | Clone repo |
| `dtolnay/rust-toolchain` | Install Rust toolchain |
| `Swatinem/rust-cache@v2` | Cache cargo artifacts |
| `actions/upload-artifact@v4` | Store build outputs |
| `softprops/action-gh-release@v2` | Create GitHub releases |
| `actions/dependency-review-action@v4` | Block vulnerable deps on PRs |
| `docker/build-push-action@v5` | Build and push Docker images |
