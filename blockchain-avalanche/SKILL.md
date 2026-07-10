---
name: blockchain-avalanche
description: 2026-current Avalanche development: Layer 1 creation/deploy, Subnet-EVM configs, validator management, ACP-176 Octane dynamic gas, gas optimization, Warp Messaging, security best practices, edge cases, and troubleshooting. Use for L1 launches, validator ops, gas audits, or Avalanche infra.
version: 1.0.0
---

# Avalanche Blockchain

## Layer 1 Architecture
Avalanche Layer 1s (formerly Subnets) are sovereign, application-specific L1s with custom VMs, tokens, gas, and validators. They interoperate via L0 and Warp Messaging. 80+ live L1s in 2026.

- **Primary Network**: P, X, C-Chains (AVAX gas).
- **Custom L1s**: Subset of Primary validators (80%+ weight required for liveness).
- **VMs**: Subnet-EVM (EVM-compatible), custom VMs.

## Creating & Launching L1s
```bash
# 1. Create local L1 (avalanche-cli)
avalanche subnet create myl1
avalanche subnet deploy myl1 \
  --chain-config '{"precompileAllowList": ["0x01"], "dynamicFees": true}'
```

**Production Checklist**:
- **Min 5 validators** (weight ≥20 each, stagger expiration).
- **80%+ weighted stake online** (monitor `platform.getCurrentValidators()`).
- **VM ID naming**: Rename `subnet-evm` → `<VMID>` in `~/avalanchego/plugins/`.
- **Upgrade strategy**: Stagger nodes/VMs, verify `info.isHealthy()` and `connected: true`.

## Validator Management
```bash
# Add validator (from L1 owner wallet)
avalanche platform add-validator \
  --public-key <NODEID> \
  --start-time <TIMESTAMP> \
  --end-time <TIMESTAMP+1y> \
  --weight 100 \
  --stake-amount 2000 \
  --reward-address <ADDR> \
  --validation-reward-fee-percent 2

# Check health
curl -X POST --data '{
  "jsonrpc":"2.0", "id":1, "method":"info.isHealthy"
}' -H 'content-type:application/json;' 127.0.0.1:9650/ext/info
```

**Edge Cases**:
- <80% stake → degraded finality → halt.
- Coordinated expiry → halt; stagger by ≥1 day.
- Single validator offline → liveness risk (need ≥5).

## Subnet-EVM Configs
`~/.avalanchego/configs/chains/<chainID>/config.json`:

```json
{
  "pruning-enabled": true,
  "commit-interval": 4096,
  "rpc-gas-cap": 50000000,
  "rpc-tx-fee-cap": 100,
  "trie-clean-cache": 512,
  "trie-dirty-cache": 512,
  "warp-api-enabled": true,
  "validators-api-enabled": true,
  "dynamicFees": true,
  "precompileAllowList": ["0x01", "0x42"]
}
```

**Gas Limits** (post-Octane ACP-176):
- Dynamic target gas (validator-voted, ~15M→higher for TPS).
- BaseFee spikes after large blocks mitigated.
- Config: `min-delay-target` for block timing.

## Gas Optimization (EVM L1s)
**Storage (100x costlier than memory)**:
- Pack variables: `uint256 a; uint256 b;` → `uint256 packed = (a<<128)|b;`.
- Use `calldata` over `memory` in functions.

**Precompiles**:
- Use native ECDSA/SHA256 (cheaper than EVM opcodes).

**Other**:
- `immutable` vars (no storage).
- Short-circuit `require()` early.
- `unchecked {}` for safe math.
- L2-like: Custom L1s avoid P/C congestion.

**Edge Case**: Dynamic gas target spikes → monitor validator prefs.

## Security Best Practices
- **Staking**: ≥5 validators, monitor uptime 100%.
- **Upgrades**: Stagger, verify VMID/plugins.
- **Precompiles**: Restrict deployers/tx submitters.
- **Secrets**: Keystore external signer, no env secrets.
- **Pruning**: `pruning-enabled: true`, `allow-missing-tries: false`.
- **API**: Disable `admin-api-enabled` in prod.

**Halt Risks**:
- Validator weight < `snow-sample-size` (20).
- Coordinated downtime/offline stake <20%.

## Warp Messaging (AWM)
Enable: `"warp-api-enabled": true`. Cross-L1 atomic txs.

```solidity
// Example: Warp precompile (0x42)
function sendWarpMsg(address toChain, bytes calldata payload) external;
```

## Troubleshooting
| Issue | Check |
|-------|-------|
| L1 halted | `platform.getCurrentValidators()` stake ≥80% |
| High gas | Validator gas target low; vote higher |
| VM mismatch | Plugin named `<VMID>` |
| Sync slow | `state-sync-enabled: true` |

**Notes**: Octane live on C-Chain/Mainnet; L1s >80 live. Use Avalanche-CLI/Docker for prod infra.
