---
name: blockchain-contract-safety
description: Mandatory safety patterns for smart contracts — reentrancy, integer overflow, checks-effects-interactions, access control, and front-running. Use BEFORE writing or auditing ANY contract. NOT optional; do not skip.
version: 1.0.0
---

# Skill: Smart-Contract Safety
## System Reference: Adversarial, Immutable, Value-Bearing Code (RFC-Style Engineering Spec)

### 1. Core Model
Smart contracts hold real value, are **immutable** once deployed, and run in a public adversarial environment where every input is hostile and every caller is a potential attacker. A single flaw is an immediate, irreversible, public exploit. The canonical bug classes:

**Reentrancy.** An external call hands control to untrusted code *before* state is updated; the callee re-enters and exploits stale state (the DAO, 2016). Fix: **checks-effects-interactions** — validate (`checks`), mutate your own state (`effects`), only then call external code (`interaction`); or use a **reentrancy guard** (a lock flag / mutex).

**Integer overflow/underflow.** Pre-0.8 Solidity wrapped around; post-0.8 it reverts but `unchecked{}` and custom math still overflow. Audit every arithmetic on user-controlled inputs.

**Access control.** Missing `onlyOwner`/role checks let anyone call privileged functions (Parity multi-sig, 2017). Every state-changing function must prove who can call it.

**Front-running / MEV.** The mempool is public; bots copy profitable txs and sandwich them. Commit-reveal, slippage limits, and private order flow mitigate.

**Unchecked external calls.** `call` returns a bool; ignoring it silently swallows failure. Always check the return value.

### 2. Operational Rules
* **Rule 1 (Checks-Effects-Interactions):** validate inputs → update your state → call external code, in that order, every time.
* **Rule 2 (Reentrancy guard by default):** add a non-reentrant lock to any function that calls external addresses; defense in depth alongside C-E-I.
* **Rule 3 (Explicit access control):** every external function states and enforces who may call it; default-deny.
* **Rule 4 (Safe math on user input):** never trust arithmetic on attacker-controlled values; use checked math, bounds, and overflow assertions.
* **Rule 5 (Check every external call's return):** a `call` that you don't assert on is a silent failure waiting to happen.
* **Rule 6 (Assume the mempool is adversarial):** protect against front-running with commit-reveal, deadlines, and slippage tolerances.
* **Rule 7 (Audit before immutability):** you cannot patch a deployed contract cheaply — formal review, fuzzing, and a circuit-breaker/pause are part of shipping.

### 3. Reference Implementation (Python — the guard pattern, language-neutral)
```python
# Illustrates checks-effects-interactions + a reentrancy guard.
# In Solidity this maps to `nonReentrant` modifier + ordering; in ink!/Soroban, a Cell<bool> lock.

class UnsafeVault:
    """Vulnerable: external callback fires BEFORE the balance is updated (reentrancy)."""
    def __init__(self): self.balances: dict[str, int] = {}
    def withdraw(self, who, amount, on_receive=None):
        # CHECKS
        if self.balances.get(who, 0) < amount:
            raise ValueError("insufficient")
        # INTERACTION (too early!) -> on_receive can call withdraw again, draining the vault
        if on_receive: on_receive()
        # EFFECTS (applied after the callback already saw the old balance)
        self.balances[who] -= amount

class SafeVault:
    """Correct: C-E-I ordering + a reentrancy lock."""
    def __init__(self): self.balances: dict[str, int] = {}; self._locked = False
    def withdraw(self, who, amount, on_receive=None):
        if self._locked:                              # Rule 2: reentrancy guard
            raise RuntimeError("reentrant call")
        self._locked = True
        try:
            # CHECKS
            if self.balances.get(who, 0) < amount:
                raise ValueError("insufficient")     # bounds check (Rule 4)
            # EFFECTS first
            self.balances[who] -= amount
            # INTERACTION last
            if on_receive: on_receive()
        finally:
            self._locked = False

def attack():
    vault = UnsafeVault(); vault.balances["att"] = 10
    def cb():
        if vault.balances.get("att", 0) >= 10:
            vault.withdraw("att", 10, cb)            # re-enters on stale balance
    vault.withdraw("att", 10, cb)                    # drains more than 10
    return vault.balances
# print(attack())  # balance goes negative -> the bug
```

### 4. Agent Execution Directives
* **Before writing any contract:** apply Rules 1–7 as a checklist; the contract is not done until each is satisfied.
* **On review:** trace every external call; confirm state is updated before it and that its return value is checked.
* **On any `transfer`/`call`/`send`:** verify it cannot re-enter privileged logic; prefer pull-over-push for payments.
