---
name: rust-ownership-lifetimes
description: Solves borrow-checker, lifetime, and ownership errors and designs self-referential and arena structures without unsafe. Use when fixing E0382/E0597/E0106, structuring lifetimes, or choosing Arc vs arena vs owning vs borrowing. NOT for concurrency (Send/Sync) — use rust-concurrency.
version: 1.0.0
---

# Skill: Ownership, Borrowing & Lifetimes
## System Reference: The Rust Ownership Model (RFC-Style Engineering Spec)

### 1. Core Model
Every value has exactly one **owner**; when the owner goes out of scope the value is dropped. References are **borrows**: at any instant you may have either
* one or more `&T` (shared), **or**
* exactly one `&mut T` (exclusive).

**Lifetimes** are compile-time regions tying references to the data they borrow. The compiler rejects any reference that could outlive its referent. A function's signature must express the borrowing contract:

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {   // E0106 fixed: tie output to inputs
    if x.len() > y.len() { x } else { y }
}
```
`'a` says: the returned reference lives **at most as long as the shortest input**. Lifetimes never change runtime behavior — they are proof obligations the borrow checker discharges.

**Lifetime elision**: the compiler infers lifetimes when (1) every input `&` gets one, (2) if there's exactly one input lifetime it's assigned to all elided outputs, (3) for `&self`/`&mut self` the self lifetime is assigned to elided outputs. When elision is ambiguous you get E0106 — write the lifetimes.

### 2. Operational Rules
* **Rule 1 (Aliasing XOR mutation):** you cannot mutate through a reference while another reference to the same data is live. E0382 ("moved") and E0502/E0596 ("borrow conflicts") are this rule firing.
* **Rule 2 (References never outlive data):** a borrow's lifetime must be contained in the owner's. Dangling references are impossible by construction.
* **Rule 3 (Structs borrow via a lifetime):** a struct holding a reference must declare `'a` and borrow for `'a`; prefer **owning** types (`String`, `Vec`, `Box`) in structs unless a borrow is provably better.
* **Rule 4 (Self-referential structs need `Pin`):** never build a self-referential struct by hand; use `Pin<&mut Self>` (e.g. async state machines) so the value cannot be moved after its internal pointer is formed.
* **Rule 5 (Arenas to break ownership cycles):** when many nodes must point to each other, replace `Rc<RefCell>` webs with an **arena + indices** (or a typed arena) — indexes are `Copy`, trivially shareable, and never leak cycles.

### 3. Reference Implementation (Rust)
```rust
// (a) Fixing E0597: a temporary does not live long enough.
struct Config { tag: String }
impl Config { fn tag(&self) -> &str { &self.tag } }
fn e0597_demo() {
    // BAD: let s = Config { tag: "x".into() }.tag();  // temp dropped at `;`
    // GOOD: bind the owner first.
    let cfg = Config { tag: "x".into() };
    let s: &str = cfg.tag();
    println!("{s}");
}

// (b) Struct holding a borrow must carry the lifetime (E0106 fix).
struct Parser<'a> { src: &'a str }
impl<'a> Parser<'a> {
    fn new(src: &'a str) -> Self { Self { src } }
    fn peek(&self) -> &str { self.src }
}

// (c) Arena + indices instead of an Rc/RefCell graph — no cycles, no drops.
#[derive(Default)]
struct Graph { nodes: Vec<String>, edges: Vec<(usize, usize)> }
impl Graph {
    fn add(&mut self, name: String) -> usize { self.nodes.push(name); self.nodes.len() - 1 }
    fn link(&mut self, a: usize, b: usize) { self.edges.push((a, b)); }
    fn neighbors(&self, n: usize) -> Vec<usize> {
        self.edges.iter().filter(|(a, _)| *a == n).map(|(_, b)| *b).collect()
    }
}

// (d) Self-referential / shared: use Pin for async-safe pinned data, never raw self ptrs.
use std::pin::Pin;
struct Pinned { _marker: std::marker::PhantomPinned }
fn pin_demo() {
    let _p: Pin<Box<Pinned>> = Box::pin(Pinned { _marker: std::marker::PhantomPinned });
}
```

### 4. Agent Execution Directives
* **When the borrow checker complains:** map the error to Rule 1–4 (move, shared-vs-mut, dangling temp, struct lifetime) and fix the contract, don't `clone()` reflexively — clones hide aliasing bugs.
* **When designing shared graphs:** reach for arena+indices first; `Rc<RefCell<T>>` only for genuinely cyclic, single-threaded, low-volume data.
* **When you reach for `unsafe` to "shut up the checker":** stop — it is almost always a lifetime-design error; use `rust-unsafe-ffi` discipline if truly needed.
