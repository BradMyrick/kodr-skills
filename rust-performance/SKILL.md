---
name: rust-performance
description: Optimizes Rust by profiling (perf/flamegraph), zero-copy parsing, SIMD, allocator choice, and allocation reduction. Use ONLY after correctness and benchmarks identify a real hot path. NOT for premature optimization.
version: 1.0.0
---

# Skill: Performance Optimization
## System Reference: Measure → Optimize → Re-measure (RFC-Style Engineering Spec)

### 1. Core Model
Correctness first; optimization is driven by **measurement**, never intuition. The loop:
1. **Profile** real workloads (`cargo flamegraph`, `perf record`) to find the actual hot path.
2. **Benchmark** that path (`criterion`) to get a baseline with confidence intervals.
3. **Change one thing**, re-measure; keep it only if the benchmark improves outside noise.
4. Document *why* the faster version is correct, because clever fast code is easy to get subtly wrong.

**Where Rust performance comes from:** zero-cost abstractions (monomorphization, inlining), cache-friendly data layout, minimizing allocations, branch reduction, and using the right level of parallelism. `unsafe` is rarely the lever — algorithm and data layout usually dominate.

### 2. Operational Rules
* **Rule 1 (No optimization without a measurement):** a flamegraph + criterion baseline must justify every change; "feels slow" is not a reason.
* **Rule 2 (Borrow, don't clone):** eliminate `clone()` on hot paths; `&[u8]`/`&str` over `Vec`/`String`; `Cow` when sometimes-owned.
* **Rule 3 (Layout for the cache):** prefer `struct of arrays`/`Vec<T>` packed small fields; avoid pointer-chasing (`Vec<Box<T>>`, linked lists); `#[repr(C)]`/packed only when FFI/ABI needs it.
* **Rule 4 (One allocation, not many):** reuse buffers (`&mut Vec`), preallocate (`Vec::with_capacity`), batch, and use `SmallVec`/`tinyvec` for small fixed cases.
* **Rule 5 (SIMD when the data is regular):** auto-vectorization covers simple loops; use `std::simd`/`wide`/`pulp` only where the profiler points and the math is uniform.
* **Rule 6 (Release profile matters):** `lto = "thin"`, `codegen-units = 1`, `opt-level = 3`, `panic = "abort"` (if acceptable) for the final binary; profile in release, never debug.
* **Rule 7 (Parallelize at the right granularity):** `rayon` for data-parallel CPU work; amortize per-task overhead against task size or you go slower.

### 3. Reference Implementation (Rust)
```rust
// Zero-copy parser: borrow from the input, no allocation (Rule 2).
pub struct Header<'a> { pub name: &'a str, pub value: &'a str }

pub fn parse_header(input: &str) -> Option<Header<'_>> {
    let (name, rest) = input.split_once(':')?;
    Some(Header { name: name.trim(), value: rest.trim() })
}

// Amortize allocation: caller-owned buffer, reused across calls (Rule 4).
pub fn collect_squares(input: &[u64], out: &mut Vec<u64>) {
    out.clear();
    out.reserve(input.len());
    for &x in input { out.push(x * x); }          // no realloc: capacity reserved
}

// Data-parallel CPU work at coarse granularity (Rule 7).
fn par_sum_squares(input: &[u64]) -> u64 {
    use std::sync::atomic::{AtomicU64, Ordering};
    let total = AtomicU64::new(0);
    input.par_chunks(8192).for_each(|chunk| {
        let s: u64 = chunk.iter().map(|&x| x * x).sum();
        total.fetch_add(s, Ordering::Relaxed);     // Rule 3 of rust-concurrency: Relaxed is fine here
    });
    total.load(Ordering::Relaxed)
}
// (rayon's `.par_chunks` requires the rayon crate; use `use rayon::prelude::*;` in real code.)
use std::sync::atomic::Ordering;
trait ParExt { fn par_chunks(&self, n: usize) -> std::slice::Chunks<u64>; }
impl ParExt for [u64] { fn par_chunks(&self, n: usize) -> std::slice::Chunks<u64> { self.chunks(n) } }
// NOTE: the std fallback above is sequential; rayon provides the real parallel iterator.
```

### 4. Agent Execution Directives
* **Before optimizing:** produce a flamegraph and a criterion baseline; quote the number you're trying to beat.
* **When choosing a lever:** prefer data-layout and allocation reduction over micro-tricks and `unsafe`; re-benchmark after each change.
* **When making release builds:** set `profile.release` (`lto`, `codegen-units=1`); never benchmark debug builds.
