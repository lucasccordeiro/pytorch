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
| `qkv_equivalence` | 8 | SUCCESSFUL | SUCCESSFUL | 11 s |
| `qkv_equivalence_buggy` | 8 | FAILED | FAILED | 242 s |
| `qkv_equivalence_torch` | 4 | SUCCESSFUL | SUCCESSFUL | 110 s |
| `qkv_equivalence_torch_buggy` | 4 | FAILED | FAILED | 274 s |

**4/4 targets behave as expected.** Each clean target verifies; each mutant is
refuted with a concrete counterexample (the `_buggy` runs report a violated
equivalence assertion, e.g. `qkv_equivalence_torch_buggy` violates
`assert torch.allclose(Va, Vb)`), so the suite cannot pass vacuously.

## Notes on the numbers

- **Exactness.** The clean proofs are FP-*exact* equality, not tolerance: the
  fused column `QKV[:, j]` is the identical multiply–add sequence as the
  corresponding unfused projection, so the two are bit-for-bit equal. The
  scalar encoding additionally demonstrates the tolerance form
  (`math.fabs(a-c) <= atol + rtol*|c|`).
- **Why the mutants are slow.** Refuting an FP equivalence means the solver
  searches the floating-point input space for a distinguishing assignment;
  this is markedly slower than confirming UNSAT for the clean proof (242 s vs
  11 s for the scalar pair).
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
