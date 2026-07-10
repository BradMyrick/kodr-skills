---
name: rust-error-handling
description: Structures error handling with Result, thiserror (library error enums), and anyhow/eyre (application error context). Use when designing error types, propagating with ?, or choosing a library-vs-application error strategy. NOT for using panics as control flow — avoid that.
version: 1.0.0
---

# Skill: Error Handling Strategy
## System Reference: Result + Typed Errors + Context Layering (RFC-Style Engineering Spec)

### 1. Core Model
Rust separates **recoverable** errors (`Result<T, E>`) from **unrecoverable** bugs (`panic!`). Recoverable errors flow with `?`: `foo()?` returns early with the error if `foo` failed, propagating it to the caller. `Result` forces the caller to acknowledge failure — there is no silently-ignored error.

**Two error philosophies, by layer:**
* **Library** code returns a **concrete, structured error enum** (`thiserror::Error`) so callers can `match` on variants and react.
* **Application** (binary) code aggregates heterogeneous errors into one opaque type (`anyhow::Error`/`eyre::Report`) with chained `.context()`, printed at the top level.

Mixing them backwards is the common mistake: a library returning `anyhow::Error` (un-matchable by callers) or a binary drowning in nested `Box<dyn Error>`.

### 2. Operational Rules
* **Rule 1 (Libraries: typed, exhaustive):** expose an `enum E: Error` with a variant per failure mode so `match` is exhaustive; `#[non_exhaustive]` if you may add variants later.
* **Rule 2 (Apps: one opaque type + context):** use `anyhow`/`eyre`; attach `.context("what was being done")` at every boundary so the chain reads top-down to the root cause.
* **Rule 3 (`?` converts via `From`):** `thiserror`'s `#[from]` auto-impls `From`, so `?` converts across layers automatically.
* **Rule 4 (No `unwrap`/`expect` in libraries):** they're fine in tests and invariants you can prove; in library code they turn a recoverable condition into a panic the caller cannot handle.
* **Rule 5 (Don't swallow):** never replace an error with `Ok(())`/`unwrap_or_default()` without logging or re-classifying; losing the cause is a debugging nightmare.
* **Rule 6 (Panics are for invariants):** panic only on violated invariants (logic the caller cannot trigger legitimately), never on bad input (return `Result`).

### 3. Reference Implementation (Rust)
```rust
// ---- Library layer: structured, matchable error ----
use std::path::PathBuf;

#[derive(Debug, thiserror::Error)]
pub enum LoadError {
    #[error("config not found at {0}")]
    NotFound(PathBuf),
    #[error("config parse failed: {0}")]
    Parse(#[from] toml::de::Error),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
}

pub fn load(path: &std::path::Path) -> Result<Config, LoadError> {
    let text = std::fs::read_to_string(path).map_err(LoadError::Io)?;   // Rule 3 via #[from]
    let cfg: Config = toml::from_str(&text)?;                            // Parse error auto-converts
    Ok(cfg)
}

// ---- Application layer: aggregate, add context, report at the top ----
fn run() -> anyhow::Result<()> {
    let cfg = load(std::path::Path::new("config.toml"))
        .context("loading startup config")?;           // Rule 2: add human context
    serve(cfg).context("serving requests")?;
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("error: {e:#}");   // prints the full, context-chained chain
        std::process::exit(1);
    }
}

struct Config; fn serve(_: Config) -> anyhow::Result<()> { Ok(()) }
```

### 4. Agent Execution Directives
* **When in a library:** define a `thiserror` enum with one variant per real failure mode; never leak `anyhow` across a public API.
* **When in a binary:** wrap in `anyhow`, sprinkle `.context()` at every architectural boundary so the error chain narrates *what happened and where*.
* **When reviewing:** flag every `unwrap()`/`expect()` in non-test, non-proven code; replace with `?` or explicit handling.
