---
name: blockchain-gas-mev
description: Fee markets (EIP-1559 base fee + tip), mempool dynamics, and MEV (maximal extractable value) and its mitigation. Use when modeling gas, sequencing, or front-running/sandwich risk. NOT for consensus finality — use blockchain-consensus.
version: 1.0.0
---

# Skill: Gas Economics & MEV
## System Reference: EIP-1559 Fee Market + Mempool + MEV (RFC-Style Engineering Spec)

### 1. Core Model
Because block space is scarce, a chain needs a fee market to allocate it. Ethereum's **EIP-1559** replaced blind gas-price auctions with a two-part price:

$$\text{price paid} = \min(\text{tip} + \text{base fee},\ \text{max fee (user cap)})$$

* **Base fee:** the protocol-set price per gas, adjusted per block by the gas used vs target. Above target → base fee rises; below → it falls.
$$b_{n+1} = b_n \cdot \left(1 + \tfrac{1}{8}\cdot\tfrac{\text{gas used}_n - \text{target}}{\text{target}}\right)$$
The base fee is **burned** (not paid to miners), decoupling block-size manipulation from revenue.
* **Tip (priority fee):** paid to the block producer to incentivize inclusion when demand is high.

**Mempool.** The holding area for pending transactions, visible to searchers. **MEV** is value extractable by reordering, inserting, or censoring txs within a block — the block producer (or a "searcher" paying them) can sandwich a swap, arbitrage a price gap, or front-run a liquidation.

**MEV forms:** arbitrage (DEX price gaps), liquidation (under-collateralized positions), sandwich (front-run + back-run a victim swap), and long-range copying.

**Mitigations:** slippage limits (caps victim loss), commit-reveal (hide intent until sealed), threshold encryption/encrypted mempools, and fair ordering; **proposer-builder separation (PBS)** routes MEV to the validator and can refund it to users.

### 2. Operational Rules
* **Rule 1 (Users set a max-fee ceiling):** the user never overpays their `maxFee`; when `base+tip < maxFee`, the difference is refunded.
* **Rule 2 (Base fee is inelastic to one actor):** a single producer cannot spike or crash it durably — manipulation costs more than it earns.
* **Rule 3 (Assume the mempool is watched):** any profitable pending tx will be sandwiched/arbitraged unless protected.
* **Rule 4 (Bound slippage and deadlines):** every swap/transfer-from sets `minAmountOut` and a deadline so a delayed/frontrun tx reverts instead of overpaying.
* **Rule 5 (MEV is revenue or theft):** design protocols to capture MEV for users (auctions, batch settlements) rather than leaking it to searchers.

### 3. Reference Implementation (Python — EIP-1559 base fee + sandwich impact)
```python
def next_base_fee(base: int, gas_used: int, target: int, elasticity: int = 8) -> int:
    """EIP-1559 base-fee update; elasticity denominator is 8 on Ethereum."""
    delta = base * (gas_used - target) // (target * elasticity)
    return max(base + delta, 1)            # base fee never goes below 1

def effective_price(base: int, tip: int, max_fee: int) -> int:
    """What the user actually pays per gas."""
    return min(tip + base, max_fee)

def sandwich_impact(amount_in: int, price: float, frontrun_in: int) -> tuple[int, int]:
    """Constant-product AMM: a sandwich pushes price against the victim, then back."""
    # victim gets fewer out because the frontrun moved the price up first
    victim_naive_out = int(amount_in * price)
    price_after_front = price * (1 + frontrun_in / (frontrun_in + 1))   # simplified
    victim_out = int(amount_in * price * (price / price_after_front))    # slippage
    return victim_naive_out, victim_out                                   # loss = naive - actual

if __name__ == "__main__":
    b = 10_000_000_000                                    # 10 gwei
    print("next base fee (used=target):", next_base_fee(b, 15_000_000, 15_000_000))
    print("next base fee (used>target):", next_base_fee(b, 30_000_000, 15_000_000))
    naive, real = sandwich_impact(100, 2000.0, 1000)
    print(f"sandwich loss: victim expected {naive}, got {real}")
```

### 4. Agent Execution Directives
* **When modeling fees:** use the EIP-1559 update rule and the min(tip+base, maxFee) price; don't assume a flat gas price.
* **When designing a user-facing tx:** always set slippage tolerance and a deadline (Rule 4).
* **When evaluating a protocol's economics:** ask where MEV accrues (user, protocol, or searcher) and whether the design leaks it.
