---
name: rust-unsafe-ffi
description: Reviews and writes unsafe Rust and FFI with explicit safety contracts, soundness obligations, and bindgen patterns. Use when writing or reviewing unsafe blocks, extern FFI, or proving a safe abstraction is sound. NOT a license to bypass the borrow checker casually.
version: 1.0.0
---

# Skill: unsafe Rust, FFI & Soundness
## System Reference: The Soundness Obligation (RFC-Style Engineering Spec)

### 1. Core Model
`unsafe` grants five superpowers: dereference raw pointers, call `unsafe` functions, implement `unsafe` traits, access/mutate `static mut`, and access union fields. **Crucially, `unsafe` does not turn off the borrow checker** — it shifts the burden of proof for those five operations onto the programmer. A `pub fn` marked `safe` that can be misused into **undefined behavior (UB)** is **unsound** — the cardinal sin of a Rust library.

**UB to never introduce:** data races, dereferencing invalid/null/dangling pointers, reading uninitialized memory, invalid enum discriminants, aliasing `&mut` while live, unwinding across FFI into C (`abort`), violating `Send`/`Sync` by hand.

**The safety contract** is documentation + code: every `unsafe` block carries a `// SAFETY:` comment proving the precondition holds; every `unsafe fn` carries a `# Safety` doc section stating what the caller must guarantee.

### 2. Operational Rules
* **Rule 1 (Minimize the unsafe surface):** confine `unsafe` to one module exposing a fully `safe` API; the rest of the crate is normal checked Rust.
* **Rule 2 (Every block proves its contract):** a `// SAFETY:` comment is mandatory and must justify *why* the precondition holds in this exact call site.
* **Rule 3 (FFI boundaries are untyped):** C gives you raw pointers and integers with no lifetimes; re-attach lifetimes and ownership on the Rust side immediately (`&[u8]`, `Box::from_raw`), never let raw pointers roam.
* **Rule 4 (No unwinding across FFI):** C cannot handle Rust panics; wrap FFI entry points in `std::panic::catch_unwind` or use `#[panic_handler]`/`abort` so a panic never crosses into C.
* **Rule 5 (MaybeUninit, not mem::uninitialized):** for uninitialized buffers use `MaybeUninit<T>` and initialize before reading; reading uninit memory is UB even if you "don't look."
* **Rule 6 (Send/Sync by hand is a soundness claim):** implementing `unsafe impl Send for T` asserts no data race is possible — prove it or don't write it.
* **Rule 7 (Use Miri):** run `cargo +nightly miri test` on unsafe code; it detects many UB classes at runtime.

### 3. Reference Implementation (Rust)
```rust
use std::mem::MaybeUninit;

/// Safe wrapper around an unsafe operation. Public API is fully safe.
pub fn copy_first(dst: &mut [u8], src: &[u8]) -> usize {
    let n = dst.len().min(src.len());
    // SAFETY: both pointers are valid for their respective lengths (borrowed from
    // Rust slices), `n <= min(len)`, regions do not overlap (one is &mut, one &),
    // and neither is null. The copy stays within bounds.
    unsafe { std::ptr::copy_nonoverlapping(src.as_ptr(), dst.as_mut_ptr(), n); }
    n
}

// FFI: re-attach ownership/lifetimes immediately at the boundary.
extern "C" {
    // C: int64_t sum(const int64_t* p, size_t n);
    fn sum(p: *const i64, n: usize) -> i64;
}
pub fn safe_sum(xs: &[i64]) -> i64 {
    // SAFETY: xs.as_ptr() is valid for xs.len() elements; len matches; not null.
    unsafe { sum(xs.as_ptr(), xs.len()) }
}

// MaybeUninit: reserve uninitialized memory, then write before any read (Rule 5).
pub fn zeroed_buffer(n: usize) -> Vec<u8> {
    let mut buf = Vec::with_capacity(n);
    buf.resize(n, 0u8);                         // every byte initialized before read
    buf
}

// Explicit MaybeUninit: reading uninitialized memory is UB even if you "don't look".
fn write_then_read_uninit(slot: &mut MaybeUninit<u8>) -> u8 {
    slot.write(42);                             // initialize first
    // SAFETY: the slot was just written, so reading is defined behavior.
    unsafe { slot.assume_init() }
}
mod _privacy { use super::*; } // placeholder so the snippet compiles in isolation
```

### 4. Agent Execution Directives
* **When reviewing `unsafe`:** demand a `// SAFETY:` justification per block and a `# Safety` doc per `unsafe fn`; if either is missing or hand-wavy, reject.
* **When writing FFI:** reattach ownership on the Rust side before anything else; assume C data is hostile (lengths may lie, pointers may be null).
* **When you must `unsafe impl Send/Sync`:** write the proof that no concurrent mutation is reachable; if unsure, don't.
* **Before merging unsafe code:** run Miri; a Miri failure is a blocker, not a style note.
