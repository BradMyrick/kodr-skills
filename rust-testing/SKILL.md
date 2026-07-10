---
name: rust-testing
description: Designs Rust test suites across unit, integration, property (proptest), fuzz (cargo-fuzz), and benchmark (criterion) layers. Use when writing tests, adding fuzz targets, structuring #[cfg(test)], or proving invariants. NOT for production runtime code.
version: 1.0.0
---

# Skill: Testing Strategy in Rust
## System Reference: The Test Pyramid + Property/Fuzz Layers (RFC-Style Engineering Spec)

### 1. Core Model
A correct Rust crate layers four kinds of verification, each catching a different class of bug:

| Layer | Tool | Catches |
|---|---|---|
| **Unit** | `#[test]` in `src/*.rs` under `#[cfg(test)]` | logic regressions at the function level |
| **Integration** | `tests/*.rs` (separate binary per file) | public-API contract + wiring bugs |
| **Property** | `proptest` / `quickcheck` | edge cases you didn't think to write |
| **Fuzz** | `cargo-fuzz` (libFuzzer) | panics/UB under adversarial byte input |
| **Benchmark** | `criterion` | performance regressions (statistical) |

**Property tests** express an *invariant* and let the engine search for a counterexample: `for any input X, property(X) holds`. **Fuzzing** feeds mutated bytes to a parser/decoder and crashes on panic/overflow/assertion. Unit tests prove a point; property tests and fuzzers prove a *space*.

### 2. Operational Rules
* **Rule 1 (One behavior per test):** each `#[test]` asserts one thing and has a name that reads like a spec (`parse_rejects_trailing_garbage`).
* **Rule 2 (Tests are first-class code):** use `#[cfg(test)] mod tests`, keep helpers DRY, and never test via `println!` — assert.
* **Rule 3 (Property > example for invariants):** if a function has an invariant (round-trip, monotonicity, commutativity), write a `proptest`, not three examples.
* **Rule 4 (Fuzz every untrusted boundary):** any parser, deserializer, or byte-handling function gets a `cargo-fuzz` target; UB/panics on hostile input are security bugs.
* **Rule 5 (Benchmarks need statistics):** use `criterion` (it handles warm-up, outliers, % change); never time with `Instant::now()` in a loop.
* **Rule 6 (Determinism):** seed any RNG in tests (`StdRng::seed_from_u64`); flaky tests destroy trust.

### 3. Reference Implementation (Rust)
```rust
// src/parser.rs (excerpt) + co-located unit + property tests
pub fn parse_u32(bytes: &[u8]) -> Option<u32> {
    if bytes.len() == 4 {
        Some(u32::from_le_bytes(bytes.try_into().ok()?))
    } else { None }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_four_le_bytes() {                       // Rule 1: one behavior
        assert_eq!(parse_u32(&[1, 0, 0, 0]), Some(1));
    }
    #[test]
    fn rejects_wrong_length() {
        assert_eq!(parse_u32(&[1, 0, 0]), None);
    }

    // Rule 3: a property test over the round-trip invariant.
    proptest::proptest! {
        #[test]
        fn roundtrip_does_not_lose_value(v in 0u32..u32::MAX) {
            let bytes = v.to_le_bytes();
            prop_assert_eq!(parse_u32(&bytes), Some(v));
        }
    }
}

// fuzz/fuzz_target_1.rs  (cargo +nightly fuzz add fuzz_target_1) -- Rule 4
// #![no_main]
// libfuzzer_sys::fuzz_target!(|data: &[u8]| {
//     let _ = my_crate::parse_u32(data);   // must not panic/UB on any input
// });
```

### 4. Agent Execution Directives
* **When adding a feature:** add a unit test for the happy path and a property test for the invariant; if it parses bytes, add a fuzz target.
* **When a bug is fixed:** add a regression test that fails before the fix and passes after.
* **When a test is flaky:** find the nondeterminism (unscaled RNG, time, thread ordering) and make it deterministic (Rule 6) — do not delete or rerun-until-green.
