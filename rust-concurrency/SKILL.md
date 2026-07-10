---
name: rust-concurrency
description: Designs thread-safe code with Send/Sync, Mutex/RwLock, atomics, memory ordering, and lock-free/MPSC patterns. Use when fixing Send/Sync errors, choosing lock vs lock-free, or reasoning about memory ordering and data races. NOT for async tasks — use rust-async-tokio.
version: 1.0.0
---

# Skill: Concurrency, Atomics & Memory Ordering
## System Reference: Send/Sync + Locks + The Atomic Memory Model (RFC-Style Engineering Spec)

### 1. Core Model
Rust prevents **data races at compile time** via two auto-traits:
* `Send`: a type may be **moved** to another thread.
* `Sync`: `&T` may be **shared** between threads (i.e. `T` is thread-safe for shared reads).

`T: Sync` iff `&T: Send`. Most types are `Send + Sync`; the exceptions carry interior mutability (`Cell`, `RefCell`) or raw pointers (`*const`, `*mut`).

**Locks.** `std::sync::Mutex<T>`/`RwLock<T>` give exclusive/shared access; `Mutex::lock` returns a `Result` because a panicked holder **poisons** the lock (a poisoned lock signals broken invariants — do not silently ignore).

**Atomics** (`AtomicBool/32/64/usize`, `AtomicPtr`) perform indivisible read-modify-write ops with a chosen **ordering**:
* `Relaxed` — no synchronization, only atomicity (counters where order doesn't matter).
* `Release`/`Acquire` — a Release store pairs with an Acquire load to establish a **happens-before** edge: everything before the Release is visible after the matching Acquire.
* `AcqRel` — Acquire + Release (for RMW ops at sync points).
* `SeqCst` — globally consistent total order; strongest, rarely needed, use when in doubt.

The canonical publish pattern: writer publishes data via `Release` store of a flag; readers `Acquire`-load the flag, and all writes prior to the Release are visible.

### 2. Operational Rules
* **Rule 1 (Coarse before clever):** start with a `Mutex`; move to atomics/lock-free only with a measured contention profile.
* **Rule 2 (Hold locks briefly):** never `.await` or do IO while holding a std `Mutex` (deadlock/runtime-starvation); never block on user code under a lock.
* **Rule 3 (Ordering must match the protocol):** an Acquire must pair with a Release; mismatched orderings are silent data races. Use `SeqCst` if unsure, then relax with profiling.
* **Rule 4 (Poisoning is a feature):** treat `PoisonError` as "invariants may be broken"; recover explicitly (`lock().unwrap_or_else(|e| e.into_inner())`) only when you can prove safety.
* **Rule 5 (Lock-free is not free):** lock-free structures trade lock contention for CAS retry storms, allocator pressure, and ABA risk — measure before adopting.
* **Rule 6 (std Mutex is NOT Send-aware across `.await`):** for async-held guards use `tokio::sync::Mutex` only when you must hold across `.await`; otherwise prefer `std::sync::Mutex` + short critical sections.

### 3. Reference Implementation (Rust)
```rust
use std::sync::atomic::{AtomicU64, AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

// (a) Relaxed counter — atomicity only, order irrelevant.
fn count_hits(hits: &AtomicU64) { hits.fetch_add(1, Ordering::Relaxed); }

// (b) Release/Acquire publish: data written, THEN flag published.
struct Data { value: u64 }
static READY: AtomicBool = AtomicBool::new(false);
static mut PAYLOAD: u64 = 0;   // illustration only; real code owns this behind Arc<Mutex/Atomic>

fn publish(v: u64) {
    unsafe { PAYLOAD = v; }                      // (1) write data
    READY.store(true, Ordering::Release);        // (2) publish: (1) visible to any Acquire loader
}
fn read_if_ready() -> Option<u64> {
    if READY.load(Ordering::Acquire) {            // pairs with the Release
        Some(unsafe { PAYLOAD })                  // sees (1)
    } else { None }
}

// (c) Double-checked init with once-style ordering.
#[derive(Clone)]
struct Cfg { n: u64 }
fn init_once(slot: &Mutex<Option<Cfg>>, flag: &AtomicBool) -> Cfg {
    if flag.load(Ordering::Acquire) {             // fast path
        return slot.lock().unwrap().clone().unwrap();
    }
    let mut g = slot.lock().unwrap();
    if g.is_none() {
        *g = Some(Cfg { n: 42 });
        flag.store(true, Ordering::Release);
    }
    g.clone().unwrap()
}

// (d) Shared counter across threads (Arc + Mutex, the safe default).
fn shared_counter_demo() {
    let counter = Arc::new((Mutex::new(0u64), AtomicU64::new(0)));
    let handles: Vec<_> = (0..8).map(|_| {
        let c = Arc::clone(&counter);
        thread::spawn(move || { for _ in 0..1000 { c.1.fetch_add(1, Ordering::Relaxed); } })
    }).collect();
    for h in handles { h.join().unwrap(); }
    assert_eq!(counter.1.load(Ordering::Relaxed), 8000);
}
```

### 4. Agent Execution Directives
* **On `Send`/`Sync` errors:** identify the offending field (raw pointer, `Rc`, `RefCell`, non-`Sync` foreign type) and wrap it (`Arc<Mutex<T>>`, `Arc<dyn Trait + Send + Sync>`) or keep it single-threaded.
* **When choosing ordering:** default `SeqCst`, document the protocol, then downgrade to Acquire/Release with benchmarks; never `Relaxed` for cross-thread signaling.
* **When contention bites:** measure under real load before replacing a `Mutex` with a lock-free structure; ABA and memory-reclamation (epoch/hazard pointers) are the real costs.
