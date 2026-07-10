---
name: ai-mixed-precision
description: Mixed-precision training — fp32/bf16/fp16/fp8, dynamic loss scaling, and tensor-core utilization. Use when speeding up or memory-sizing training, or debugging NaN/overflow. NOT for integer quantization of weights post-training.
version: 1.0.0
---

# Skill: Mixed-Precision Training
## System Reference: Numeric Formats + Loss Scaling + Tensor Cores (RFC-Style Engineering Spec)

### 1. Core Model
Training in fp32 is correct but slow and memory-heavy. **Mixed precision** keeps a **master copy** in fp32 for accuracy-critical updates while computing forward/backward in a lower-precision format on **tensor cores** (which multiply bf16/fp16/fp8 matrices at many× the fp32 rate).

**The formats:**
| Format | Bytes | Range | Mantissa | Use |
|---|---|---|---|---|
| **fp32** | 4 | wide | 23-bit | master weights, optimizer, reductions |
| **fp16** | 2 | narrow (~±65k) | 10-bit | compute (needs **loss scaling**) |
| **bf16** | 2 | same range as fp32 | 7-bit | compute (no loss scaling needed) |
| **fp8** | 1 | narrow (E4M3/E5M2) | 3-bit | newest; needs per-tensor scaling |

**Why bf16 wins on GPUs:** same dynamic range as fp32 (no overflow) but fewer mantissa bits → **no loss scaling required**, so bf16 is the modern default. fp16 needs **dynamic loss scaling** to prevent the tiny gradients from underflowing to zero: scale the loss up by $S$ before backward (so gradients stay in fp16 range), then divide grads by $S$ before the optimizer step; if a grad overflows, skip the step and halve $S$.

**fp8** doubles throughput/memory again but needs careful **per-tensor scaling** (delayed scaling or dynamic) to map values into the tiny representable range without overflow/underflow.

**Reductions:** always reduce gradients in fp32 (accumulate into fp32 buffers) — reducing in fp16/bf16 loses precision across thousands of partial sums.

### 2. Operational Rules
* **Rule 1 (Default to bf16):** same range as fp32, no loss scaling; use fp16 only on hardware without bf16.
* **Rule 2 (Master weights in fp32):** keep fp32 master copies + optimizer state; update from the unscaled fp32 grads.
* **Rule 3 (Scale then unscale for fp16):** dynamic loss scaling; skip+halve on overflow.
* **Rule 4 (Reduce in fp32):** AllReduce/accumulator buffers are fp32, even if compute is bf16.
* **Rule 5 (fp8 needs per-tensor scales):** use framework autocalibration; watch for silent accuracy drift over training.
* **Rule 6 (NaN ⇒ overflow):** a sudden NaN mid-training usually means a grad overflow or an fp8 scale blowup — check loss scaling before blaming the data.

### 3. Reference Implementation (Python — dynamic loss scaling)
```python
class DynamicLossScaler:
    """fp16 dynamic loss scaling (Rule 3): scale up, unscale grads, skip+halve on overflow."""
    def __init__(self, init_scale: float = 2**16, backoff: float = 0.5,
                 growth: float = 2.0, growth_interval: int = 2000):
        self.scale = init_scale; self.backoff = backoff
        self.growth = growth; self.growth_interval = growth_interval
        self.steps_since_growth = 0

    def step(self, grads_max_abs: float):
        """Call after computing grads (already multiplied by scale)."""
        if not isfinite(grads_max_abs) or grads_max_abs > 65504:    # fp16 overflow
            self.scale *= self.backoff                              # Rule 3: skip + halve
            self.steps_since_growth = 0
            return "skip"                                           # drop this optimizer step
        self.steps_since_growth += 1
        if self.steps_since_growth >= self.growth_interval:
            self.scale *= self.growth                               # try to grow back
            self.steps_since_growth = 0
        return "unscale"                                            # divide grads by self.scale

def isfinite(x: float) -> bool:
    return x == x and x not in (float("inf"), float("-inf"))

if __name__ == "__main__":
    sc = DynamicLossScaler()
    for g in (1.0, 70000.0, 1.0):                                   # 70000 overflows fp16
        action = sc.step(g)
        print(f"grad_max={g:8.1f} -> {action:7s} scale={sc.scale:.0f}")
```

### 4. Agent Execution Directives
* **When sizing throughput/memory:** default bf16 (2× memory win + tensor cores); reach for fp8 only on supported hardware with per-tensor scaling.
* **On training NaN:** check the loss scaler/grad overflow before the data (Rule 6).
* **When porting fp16→bf16:** remove loss scaling (bf16 needs none) and expect slightly noisier low bits.
