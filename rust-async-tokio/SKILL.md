---
name: rust-async-tokio
description: Designs async/tokio runtimes, tasks, cancellation, backpressure, and LocalSet for non-Send futures. Use when writing async code, fixing "future cannot be sent between threads" errors, or structuring graceful shutdown. NOT for sync locks/atomics — use rust-concurrency.
version: 1.0.0
---

# Skill: Async Rust & the Tokio Runtime
## System Reference: Cooperative Futures + Runtime Executor (RFC-Style Engineering Spec)

### 1. Core Model
`async fn` returns a **`Future`**: a state machine that is `poll`ed by an **executor** to completion. Futures do nothing until polled — they are **lazy**. A `Future::poll` returns `Poll::Ready(v)` or `Poll::Pending` after registering a `Waker` the runtime will call when progress is possible. This is cooperative: a future that never yields (no `.await`) **starves** the executor.

**Runtimes.** `tokio` is the de-facto choice. `#[tokio::main]` boots a multi-thread runtime that can move tasks across worker threads — so spawned tasks must be `Send`. `tokio::task::LocalSet` runs `!Send` futures on a **single thread** (the home for capnp-rpc, thread-local state, GPU handles, GUI types).

**Cancellation** is implicit: dropping a future stops polling it at its next `.await` point. Structured cancellation uses `tokio_util::sync::CancellationToken`; `tokio::select!` cancels the losing branches.

**Backpressure** comes from **bounded channels** (`tokio::sync::mpsc`): a full channel applies backpressure to the producer via `.await`, preventing unbounded queueing and OOM.

### 2. Operational Rules
* **Rule 1 (Don't block the executor):** never call long synchronous CPU/IO (`std::thread::sleep`, blocking `read`, hashing gigabytes) on a runtime thread — use `tokio::task::spawn_blocking`.
* **Rule 2 (Cancellation lands at `.await`):** a future only observes cancellation between polls; resources held across an `.await` must be release-safe (RAII guards, not manual cleanup).
* **Rule 3 (Bounded = backpressure):** prefer bounded channels; unbounded channels hide overload until OOM.
* **Rule 4 (`Send` is about crossing threads):** "future cannot be sent between threads" means a `!Send` type is held across an `.await` on a multi-thread runtime — fix by pinning to a `LocalSet`, by `spawn_blocking`, or by ending the borrow before the `.await`.
* **Rule 5 (Structured concurrency):** spawn tasks whose lifetimes you control; drive shutdown with a `CancellationToken`/`JoinSet` so children never outlive their parent.

### 3. Reference Implementation (Rust)
```rust
use tokio::sync::mpsc;
use tokio_util::sync::CancellationToken;

// Backpressure via a bounded channel (Rule 3) + structured cancellation (Rule 5).
async fn producer(tx: mpsc::Sender<u64>, cancel: CancellationToken) {
    let mut n = 0u64;
    loop {
        tokio::select! {
            _ = cancel.cancelled() => { println!("producer stopping"); return; }
            // send().await blocks (backpressure) when the buffer is full
            res = tx.send(n) => { if res.is_err() { return; } n += 1; }
        }
    }
}

async fn consumer(mut rx: mpsc::Receiver<u64>) {
    while let Some(v) = rx.recv().await { println!("got {v}"); }
}

// !Send futures on one thread via LocalSet (Rule 4): capnp-rpc, thread-locals, GUI.
async fn non_send_work() {
    let _local: std::cell::Cell<u32> = std::cell::Cell::new(0); // !Send
    // ... capnp-rpc client setup that requires !Send objects ...
}

#[tokio::main]
async fn main() {
    let cancel = CancellationToken::new();
    let (tx, rx) = mpsc::channel::<u64>(8);              // bounded -> backpressure
    let p = tokio::spawn(producer(tx, cancel.clone()));
    let c = tokio::spawn(consumer(rx));

    tokio::time::sleep(std::time::Duration::from_millis(5)).await;
    cancel.cancel();                                       // graceful, structured shutdown
    let _ = tokio::join!(p, c);

    // A !Send workload belongs in a LocalSet on the current-thread runtime.
    tokio::task::LocalSet::new().run_until(async {
        non_send_work().await;
    }).await;
}
```

### 4. Agent Execution Directives
* **On "future cannot be sent between threads":** trace the `!Send` type held across an `.await`; the fix is LocalSet, `spawn_blocking`, or ending the borrow — not `.clone()` panic-fixing.
* **When latency spikes:** audit for blocking calls on runtime threads (Rule 1) and unbounded queues (Rule 3).
* **When shutting down:** use a `CancellationToken` + `JoinSet`; never `abort()` a task that owns resources without ensuring RAII release.
* **For capnp-rpc:** the entire client typically lives in one `LocalSet` (it is `!Send`); see `rust-capnp`.
