---
name: rust-traits-api
description: Designs ergonomic public APIs via traits, generics, associated types, sealed traits, newtypes, builders, and type-state. Use when designing a public API, choosing dyn vs impl Trait, or making illegal states unrepresentable. NOT for borrow/lifetime errors — use rust-ownership-lifetimes.
version: 1.0.0
---

# Skill: Trait & API Design
## System Reference: Type-Driven, Sealed, Builder APIs (RFC-Style Engineering Spec)

### 1. Core Model
Good Rust APIs use the type system to make **illegal states unrepresentable**: the compiler rejects misuse, so you write fewer runtime checks. The building blocks:

* **Generics + traits (static dispatch):** `fn f<T: Trait>(x: T)` monomorphizes — zero-cost, fastest, but each `T` bloats the binary.
* **`dyn Trait` (dynamic dispatch):** `fn f(x: &dyn Trait)` is one function, vtable-dispatched — smaller binary, slight runtime cost, object-safety constraints (no generics-by-value, `Self: Sized` care).
* **Associated types:** when a trait has exactly one logical output type per implementor (`trait Iter { type Item; }`) — use them over extra generic params to keep signatures clean.
* **Sealed traits:** prevent downstream crates from implementing your trait, so you can extend it without a breaking change.
* **Newtype:** `struct Years(i32)` gives a distinct type (no confusion with `Days`) at zero cost.
* **Builder:** for many optional fields; return `Self` to chain, finish with a `build()` method.
* **Type-state:** encode state in the type system (`Locked` vs `Unlocked`) so illegal transitions don't compile.

### 2. Operational Rules
* **Rule 1 (Make misuse unrepresentable):** prefer distinct types/enums over `bool`/`Option` flags that the caller can get wrong.
* **Rule 2 (Seal extensible traits):** seal public traits you may evolve; unsealed = semver trap.
* **Rule 3 (Default to generics):** choose `impl Trait`/generics for performance; reach for `dyn` only when you need runtime polymorphism (heterogeneous collections, plugins).
* **Rule 4 (Builders finish loudly):** the terminal `.build()` returns `Result` when construction can fail, else the configured value.
* **Rule 5 (Associated type when 1:1):** use an associated type when there's one output type per impl; a generic parameter when the caller picks it.
* **Rule 6 (Document the public surface):** every `pub` item gets a doc comment and an example (`///` + `# Examples`); `cargo doc` is your API reference.

### 3. Reference Implementation (Rust)
```rust
// (a) Sealed trait: downstream cannot impl it, so we may extend freely.
mod sealed { pub trait Sealed {} }
pub trait Id: sealed::Sealed { fn as_u64(&self) -> u64; }

pub struct UserId(u64);
impl sealed::Sealed for UserId {}
impl Id for UserId { fn as_u64(&self) -> u64 { self.0 } }

// (b) Associated type (1:1 output) + generic over input the caller chooses.
pub trait Store { type Out; fn get(&self, k: &str) -> Option<Self::Out>; }

// (c) Type-state: illegal transitions don't compile.
pub struct Unlocked;
pub struct Locked;
pub struct Vault<State>(std::marker::PhantomData<State>);

impl Vault<Unlocked> {
    pub fn new() -> Self { Self(std::marker::PhantomData) }
    pub fn lock(self) -> Vault<Locked> { Vault(std::marker::PhantomData) }
}
impl Vault<Locked> {
    pub fn unlock(self) -> Vault<Unlocked> { Vault(std::marker::PhantomData) }
    pub fn read(&self) -> &'static str { "secret" }   // only callable when Locked
}

// (d) Builder with a loud finish.
pub struct Server { pub port: u16, pub tls: bool }
pub struct ServerBuilder { port: Option<u16>, tls: bool }
impl Default for ServerBuilder { fn default() -> Self { Self { port: None, tls: false } } }
impl ServerBuilder {
    pub fn port(mut self, p: u16) -> Self { self.port = Some(p); self }
    pub fn tls(mut self) -> Self { self.tls = true; self }
    pub fn build(self) -> Result<Server, &'static str> {       // Rule 4: loud finish
        let port = self.port.ok_or("port is required")?;
        Ok(Server { port, tls: self.tls })
    }
}

// Usage that the type system blesses:
fn main() {
    let _u: Vault<Unlocked> = Vault::new();
    let locked = _u.lock();
    let _ = locked.read();          // compiles: Locked
    // Unlocked.read() would not compile -> illegal state unrepresentable (Rule 1)
    let srv = ServerBuilder::default().port(443).tls().build().unwrap();
    println!("{} {}", srv.port, srv.tls);
}
```

### 4. Agent Execution Directives
* **When designing an API:** enumerate the misuse cases first, then choose types (newtype, enum, type-state, sealed) that forbid them at compile time.
* **When choosing dyn vs generic:** profile; default to generic + `impl Trait`, switch to `dyn` only for true runtime polymorphism.
* **When you might extend a trait:** seal it now; an unsealed public trait is a future breaking change.
