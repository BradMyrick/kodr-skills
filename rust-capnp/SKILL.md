---
name: rust-capnp
description: Cap'n Proto schema design, Rust capnp-rpc bindings, async RPC server/client patterns, zero-copy message building and parsing, schema evolution, and interop with tokio for transport. Use when working with .capnp schema files, capnp-rpc, or high-performance IPC.
version: 1.0.0
---

# Cap'n Proto (capnp)

## Overview
Cap'n Proto is a zero-copy serialization and RPC protocol. In Rust, use the `capnp` crate for message building/parsing and `capnp-rpc` for async RPC over any async I/O transport.

## Schema Design
Define messages in `.capnp` files. Use `struct` for data, `interface` for RPC services.

```capnp
@0xdeadbeefdeadbeef;

struct AgentMessage {
  id    @0 :UInt64;
  name  @1 :Text;
  payload @2 :Data;
}

interface AgentService {
  dispatch @0 (msg :AgentMessage) -> (result :Text);
}
```

- Always assign unique 64-bit file IDs with `capnpid` or `capnp id`.
- Fields are numbered starting at `@0` — never reuse or skip field numbers when evolving schemas.
- For backwards compatibility: only add new fields at the end; never remove or reorder.

## Rust Build Integration
Use `capnpc` in `build.rs` to auto-generate Rust bindings:

```toml
# Cargo.toml
[build-dependencies]
capnpc = "0.20"

[dependencies]
capnp = "0.20"
capnp-rpc = "0.20"
```

```rust
// build.rs
fn main() {
    capnpc::CompilerCommand::new()
        .file("src/schema/agent.capnp")
        .run()
        .expect("capnp schema compilation failed");
}
```

Include generated code with:
```rust
pub mod agent_capnp {
    include!(concat!(env!("OUT_DIR"), "/agent_capnp.rs"));
}
```

## Message Building and Parsing
```rust
use capnp::message::{Builder, ReaderOptions};
use crate::agent_capnp::agent_message;

// Build
let mut msg = Builder::new_default();
{
    let mut root = msg.init_root::<agent_message::Builder>();
    root.set_id(42);
    root.set_name("seekr");
}
let mut buf = Vec::new();
capnp::serialize::write_message(&mut buf, &msg)?;

// Parse
let reader = capnp::serialize::read_message(
    &mut buf.as_slice(),
    ReaderOptions::new(),
)?;
let root = reader.get_root::<agent_message::Reader>()?;
println!("{}", root.get_name()?.to_str()?);
```

## RPC Server Pattern (with tokio)
See `tokio-localset` skill — capnp-rpc requires `LocalSet` because its futures are not `Send`.

```rust
use capnp_rpc::{rpc_twoparty_capnp, twoparty, RpcSystem};
use futures::AsyncReadExt;

pub async fn serve(stream: tokio::net::TcpStream) -> anyhow::Result<()> {
    let (reader, writer) =
        tokio_util::compat::TokioAsyncReadCompatExt::compat(stream).split();

    let network = twoparty::VatNetwork::new(
        futures::io::BufReader::new(reader),
        futures::io::BufWriter::new(writer),
        rpc_twoparty_capnp::Side::Server,
        Default::default(),
    );

    let service = build_capability(); // returns a capnp Client
    let rpc = RpcSystem::new(Box::new(network), Some(service.client));
    tokio::task::spawn_local(rpc).await??;
    Ok(())
}
```

## Common Pitfalls
- `capnp-rpc` futures are **not `Send`** — always run inside `tokio::task::LocalSet`.
- Avoid holding a `capnp::Result` across `.await` points; re-request the reader after each await.
- Use `capnp::Error` not `anyhow` for internal capnp boundaries; convert at the service boundary.
- Use `pipelined_get_*` for pipeline calls to avoid round trips.
