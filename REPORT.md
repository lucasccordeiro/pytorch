# REPORT — verification results

## Environment

- **ESBMC**: `master` (≥ [#5131](https://github.com/esbmc/esbmc/pull/5131),
  merged `502acb6570`), which includes the torch operational model
  ([#5120](https://github.com/esbmc/esbmc/pull/5120)) and the homogeneous
  nested-list element-type fix (#5131, Fixes #5129). Measured on the merge-base
  build `fdf8742186` + the #5131 patch, which is identical to current master.
- **Solver**: default (Bitwuzla 0.9.0), bit-vector / floating-point arithmetic.
- **Platform**: macOS arm64.
- **Driver**: `python3 verify.py` (`make verify`).

The torch-native targets require both #5120 (for `torch.mm` / `torch.allclose`)
and #5131 (without it, `qkv_equivalence_torch` aborts in the SMT FP encoder —
this was issue #5129, now fixed). Both are on `master`, so a current build runs
the whole suite. The scalar targets require neither.

## Results

| Target | `--unwind` | Expected | Verdict | Time |
| --- | --- | --- | --- | --- |
| `qkv_equivalence_exact` | 8 | SUCCESSFUL | SUCCESSFUL | 6 s |
| `qkv_equivalence` (tolerance) | 8 | SUCCESSFUL | SUCCESSFUL | 11 s |
| `qkv_equivalence_buggy` | 8 | FAILED | FAILED | 242 s |
| `qkv_equivalence_torch_exact` | 4 | SUCCESSFUL | SUCCESSFUL | 135 s |
| `qkv_equivalence_torch` (tolerance) | 4 | SUCCESSFUL | SUCCESSFUL | 110 s |
| `qkv_equivalence_torch_buggy` | 4 | FAILED | FAILED | 274 s |
| `bias_linear` (tolerance) | 4 | SUCCESSFUL | SUCCESSFUL | 113 s |
| `bias_linear_buggy` | 4 | FAILED | FAILED | 31 s |
| `reassoc_fusion_exact` | 2 | FAILED | FAILED (+ c.ex.) | 15 s |

**9/9 targets behave as expected.** Each clean target verifies; each mutant is
refuted with a concrete counterexample (the `_buggy` runs report a violated
equivalence assertion, e.g. `qkv_equivalence_torch_buggy` violates
`assert torch.allclose(Va, Vb)`), so the suite cannot pass vacuously.

- **Reassociation counterexample (the BMC sweet spot).** `reassoc_fusion_exact`
  reorders a 3-term reduction — sound over the reals, **unsound in IEEE-754**.
  ESBMC `--floatbv` refutes the exact equality in ~15 s and returns a concrete
  **1-ULP counterexample** (`ref` and `opt` differ in the last bit). This is the
  capability neither Lean nor ESBMC `--ir` (reals) can provide. The matching
  *tolerance* bound (`reassoc_fusion_tol.py`) is true and provable in principle,
  but proving it over the whole bit-precise FP space did **not** converge in
  ~11 min — so it is kept out of the default suite. The asymmetry is the lesson:
  with BMC, **finding a counterexample is cheap; proving an FP bound everywhere
  is expensive.**

## Notes on the numbers

- **Exact and tolerance, both proved.** For QKV we verify the equivalence two
  ways. The `_exact` targets assert **bit-for-bit equality** (scalar `==`;
  torch `allclose(rtol=0, atol=0)`) — sound because the fused column
  `QKV[:, j]` is the *identical* multiply–add sequence as the unfused
  projection. The tolerance targets assert `torch.allclose`'s real predicate
  (`|a-c| <= atol + rtol*|c|`, defaults `rtol=1e-5, atol=1e-8`), matching how
  PyTorch users actually compare tensors. Exact is the stronger claim; both
  hold here.
- **Mutant timing varies.** Refuting an FP equivalence means the solver
  searches the floating-point input space for a distinguishing assignment. When
  the discrepancy is structural and easy to witness this is fast
  (`bias_linear_buggy`, 31 s — any non-zero `b` distinguishes), but a
  tolerance-guarded scalar mismatch can be much slower than the clean proof
  (`qkv_equivalence_buggy`, 242 s vs 11 s).
- **Why the dims are small.** The torch targets stay at S=1, D=2, H=1: four
  `torch.mm` calls over the operational model already cost ~100 s, and
  nested-list construction/deep access is the dominant cost
  ([#5121](https://github.com/esbmc/esbmc/issues/5121)). Larger dims await that
  perf work.
- **Soundness of the bound.** Dimensions are fixed, so `--unwind` is concrete:
  every loop bound is known, and unwinding assertions are left **on**, so an
  insufficient bound surfaces as an unwinding-assertion violation (a safe
  failure), never as a false SUCCESSFUL. The chosen bounds (`8` scalar, `4`
  torch) fully unwind every loop including the `3H`-column fused matmul.
- **Operational-model faithfulness — measured.** The result is *modulo* the OM
  (`torch.py`) matching real PyTorch. A differential test (`validation/`) runs the
  OM's `mm`/`cat`/`split`/`allclose` against `torch` on thousands of random
  float64 inputs: **`cat`/`split`/`allclose` are bit-exact**; **`mm` agrees up to
  IEEE-754 rounding** (max relative error ~4e-13) but is **not bit-identical**
  (torch uses a different reduction order). So the OM is a faithful reference up
  to rounding, and the QKV equivalence is bit-exact *within the OM's sequential
  order* — not a bit-for-bit claim about a deployed `torch.mm`.
