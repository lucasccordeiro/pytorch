# ROADMAP

Current scope is the QKV fused/unfused equivalence, in two encodings. Planned
extensions, roughly in order of dependency.

## Tier 1 — broaden the equivalence catalogue (scalar + torch-native)

- **Bias-fused linear** ✓ done (`bias_linear`): `X @ W + b` vs the augmented
  matmul `[X | 1] @ [W ; b]` — exercises an elementwise bias add over a
  `torch.mm` result (the now-fixed esbmc#5129 FP-arithmetic path).
- **Multi-head split**: reshape/split of QKV into H heads, fused vs per-head.
- **Larger dims**: scale S/D/H once nested-list construction/access perf
  (esbmc#5121) improves; today the torch targets stay at S=1, D=2, H=1 to keep
  the four matmuls within a few minutes.

## Tier 2 — fully torch-native fusion

- Replace the manual column concat/split with `torch.cat` / `torch.split` once
  they converge at useful sizes (esbmc#5121). The operational model is already
  correct; the blocker is unwinding cost (a 1×1×3 `cat`+`split` alone is
  ~2.5 min).
- A `torch.matmul` (n-D broadcasting) target once the OM models it.

## Tier 3 — numeric properties beyond exact equivalence

- Tolerance-bounded equivalence for genuinely different reduction orders
  (where FP-exact equality does *not* hold), using an explicit `allclose`
  tolerance — already prototyped in the scalar encoding.
- Overflow/NaN-freedom contracts as a phase-2 (safety) pass in `verify.py`,
  mirroring the AWS-Neuron / vLLM two-phase driver.

## Tier 3b — cross-tool comparison (done)

- ✅ **Lean (ITP) comparison** (`lean/`): the same QKV equivalence proved in Lean 4
  by `rfl`, generalised to all dimensions, over `Int` and `Float` — confirming the
  deck's BMC-vs-ITP slide empirically. Order-preserving fusion is a definitional
  identity (ITP wins generality); FP *reassociation* is false in `Float` and yields
  no Lean counterexample (BMC wins bit-precise FP + witnesses).

## Tier 4 — automation

- A k-induction completeness check per symbolic target (certify that the chosen
  `--unwind` is exhaustive, not merely bounded), recorded in `REPORT.md`.
- CI wiring once an ESBMC build with the torch OM (≥ esbmc#5120, esbmc#5131) is
  routinely available.

## Upstream dependencies

- **esbmc#5131** (merged) — unblocked the torch-native targets. ✓
- **esbmc#5121** (perf) — gates larger dims and native `cat`/`split`.
- **esbmc#5115 / #5116** (numpy/SMT) — gate a numpy-backed matmul path.
