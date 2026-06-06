# PyTorch ESBMC equivalence-verification PoC

A proof-of-concept applying [ESBMC](https://github.com/esbmc/esbmc)'s Python
frontend to **formal equivalence of two PyTorch programs** — proving that a
fused and an unfused implementation of the same computation produce identical
results for *all* admissible inputs, not just one random sample.

Driving example: the **QKV projection** in attention.

```python
# A (unfused)              # B (fused)
Q = X @ Wq                 W   = cat([Wq, Wk, Wv], dim=1)
K = X @ Wk                 QKV = X @ W
V = X @ Wv                 Q, K, V = split(QKV, ...)
```

The original harness compared one `torch.randn` sample with `torch.allclose`.
Here every input is a **bounded nondeterministic float**, so a
`VERIFICATION SUCCESSFUL` is a proof of equivalence over the whole input range.

## Status

**8 verification targets.** QKV is proved both **bit-for-bit exact** and within
`torch.allclose`'s **tolerance**, in two encodings; each clean target is paired
with a refuted `_buggy` mutant:

| Target | Property | Verdict |
| --- | --- | --- |
| `qkv_equivalence_exact` | QKV scalar, **bit-for-bit exact** (`==`) | SUCCESSFUL |
| `qkv_equivalence` | QKV scalar, **tolerance** (`allclose` defaults) | SUCCESSFUL |
| `qkv_equivalence_buggy` | scalar, K reads V's columns | FAILED |
| `qkv_equivalence_torch_exact` | QKV **torch-native**, exact (`allclose` rtol=0, atol=0) | SUCCESSFUL |
| `qkv_equivalence_torch` | QKV **torch-native**, tolerance (`torch.mm` + `torch.allclose`) | SUCCESSFUL |
| `qkv_equivalence_torch_buggy` | torch, split swaps K/V | FAILED |
| `bias_linear` | `X@W + b` vs. augmented `[X\|1] @ [W;b]`, torch-native | SUCCESSFUL |
| `bias_linear_buggy` | fused unit column zeroed, bias dropped | FAILED |
| `reassoc_fusion_exact` | **reassociating** reduction, exact (`==`) — unsound in FP | FAILED (+ c.ex.) |

`reassoc_fusion_exact` is the bug-finding showcase: a reduction reorder that is
sound over the reals but **unsound in IEEE-754**, which ESBMC `--floatbv` refutes
with a concrete **1-ULP counterexample** — the capability neither Lean nor ESBMC
`--ir` (reals) provides. Its tolerance counterpart (`reassoc_fusion_tol.py`) is
provable but expensive, so it is kept out of the default suite (see `REPORT.md`).

The `_exact` targets prove the two programs **bit-for-bit equal** (zero
tolerance) — sound because the fused computation is the *identical* multiply–add
sequence as the unfused one; the other targets prove equality within
`torch.allclose`'s real tolerance, matching how PyTorch users compare tensors.
Each mutant is refuted with a counterexample, so the suite cannot pass
vacuously. Full results and timings in [`REPORT.md`](./REPORT.md).

The torch-native targets are the headline: they exercise the **torch
operational model** merged into ESBMC ([esbmc#5120](https://github.com/esbmc/esbmc/pull/5120))
together with the nested-list element-type fix
([esbmc#5131](https://github.com/esbmc/esbmc/pull/5131), merged; Fixes
[esbmc#5129](https://github.com/esbmc/esbmc/issues/5129)) that this PoC
surfaced. Both are on ESBMC `master`, so a current build runs the whole suite;
the scalar encoding needs neither and is the portable baseline.

## ESBMC contributions surfaced by this PoC

Driving the equivalence proof through ESBMC's Python list model exposed a chain
of frontend defects; several are now fixed upstream. Full ledger in
[`AUDIT.md`](./AUDIT.md).

- **Merged:** nested-list cross-function return value/type
  ([#5111](https://github.com/esbmc/esbmc/pull/5111), fixes #5102/#5103),
  list-copy element corruption ([#5113](https://github.com/esbmc/esbmc/pull/5113)),
  the torch operational model ([#5120](https://github.com/esbmc/esbmc/pull/5120)),
  homogeneous nested-list element-type resolution
  ([#5131](https://github.com/esbmc/esbmc/pull/5131), fixes #5129).
- **Open issues:** numpy symbolic matmul bounds (#5115), nested-list matmul
  SMT SIGABRT (#5116), nested-list perf (#5121), double-subscript-binop parse
  SIGABRT (#5122).

## Running

```bash
# Point ESBMC at a current master build (>= esbmc#5131, which also includes
# the torch OM esbmc#5120 — both needed for the torch-native targets):
make verify ESBMC=/path/to/esbmc/build/src/esbmc/esbmc

# Or a single target:
ESBMC=/path/to/esbmc python3 verify.py qkv_equivalence_torch
```

`verify.py` runs ESBMC on each `harness/<name>.py` and checks the verdict
against the manifest. See [`ROADMAP.md`](./ROADMAP.md) for planned targets and
[`RETROSPECTIVE.md`](./RETROSPECTIVE.md) for the modelling pitfalls (NaN, loop
truncation, tolerance predicates, `cat`/`split` cost) learned along the way.

## Layout

```
harness/
  stubs.py                         shared bounded-nondet-float helper
  qkv_equivalence.py               scalar QKV equivalence: tolerance, _exact, _buggy
  qkv_equivalence_torch.py         torch-native QKV: tolerance, _exact, _buggy
  bias_linear.py                   bias-fused linear equivalence    (+ _buggy)
  reassoc_fusion_exact.py          reassociating reduction: refuted (+ _tol, slow)
  esbmc_defects/                   minimal reproducers for the ESBMC bugs found
validation/                        differential test of the OM vs real PyTorch
verify.py                          suite driver
Makefile                           `make verify`
README / REPORT / AUDIT / ROADMAP / RETROSPECTIVE.md
```
