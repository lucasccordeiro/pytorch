# RETROSPECTIVE — modelling pitfalls

Lessons from getting a PyTorch equivalence proof through ESBMC's Python
frontend. Each cost real debugging time; recording them so the next target
doesn't.

## 1. Unconstrained `nondet_float()` admits NaN

`NaN == NaN` is `False` and `NaN - NaN` is `NaN`, so a raw equality or
tolerance assertion over an unconstrained nondet float **fails spuriously**
(`x = nondet_float(); assert x == x` → FAILED). Every input must be bounded:

```python
v = nondet_float()
__ESBMC_assume(v >= -10.0)
__ESBMC_assume(v <= 10.0)
```

This is the entire job of `harness/stubs.py:bounded()`. The bound excludes
NaN/Inf and keeps the proof over a finite, well-behaved range.

## 2. Loop truncation gives *vacuous* SUCCESSFUL

`--unwind N --no-unwinding-assertions` silently truncates any loop whose bound
exceeds `N`, returning a meaningless SUCCESSFUL. The fused matmul iterates to
`3H` columns, so `--unwind` must be `>= max-loop-bound + 1` **with unwinding
assertions left on**. When the bound is symbolic, use `--k-induction` and
require convergence rather than guessing `N`. (In this PoC the dims are fixed,
so a concrete `--unwind 4` / `--unwind 8` with assertions on is exhaustive — an
unwinding-assertion violation, not a wrong answer, is what you get if `N` is too
small, which is the safe failure mode.)

## 3. Tolerance predicates must be inlined, not wrapped

Modelling `torch.allclose` as `math.fabs(a-c) <= atol + rtol*math.fabs(c)`
works **only inlined at the assertion**. Two ESBMC defects bit here (now fixed,
see AUDIT #5104/#5105): a user function *returning a float* crashed the backend,
and one *returning a float comparison* produced a wrong verdict. Use `math.fabs`
(the math OM), never a hand-written `abs`. The torch-native encoding avoids this
entirely by calling the model's `torch.allclose`, whose comparison runs inside
the FLAIL-baked model rather than in user code.

## 4. The list value/type model was the real blocker, not the math

The natural "store matrix elements in nested Python lists and run a triple-loop
matmul" approach did not verify at first: nested-list elements were corrupted on
copy/return (wrong value for ints, SMT-backend crash for floats). This was a
chain of frontend bugs (#5102/#5103), not a limitation of the arithmetic. It is
fixed now (#5111/#5113), which is exactly what made the torch operational model
viable.

## 5. `torch.cat` / `torch.split` are correct but unwinding-heavy

The model implementations are right, but their runtime-sized inner loops blow up
symbolic execution — a 1×1×3 `cat`+`split` alone takes ~2.5 min (#5121). The
practical encoding builds the fused weight matrix and splits the result by
**manual column assignment**; `torch.mm` and `torch.allclose` still go through
the OM. "Torch-native where it matters."

## 6. Double-subscript arithmetic crashes the parser

`M[i][j] - x` (any binop with a double-subscript operand) aborts at parse time
(`json.hpp:2174`, #5122) — for both constant and symbolic indices. Sidestep by
**row-extracting first**:

```python
r = M[i]
d = r[j] - x        # fine
```

All harnesses here read rows into a local before doing FP arithmetic.

## 7. The fix you ship may not be the bug you remembered

The defect this PoC chased as a "model-function wrong-verdict corruption" had,
by the time it was re-investigated on current `master`, become a *crash*
(#5129) and turned out to be a residual of the already-fixed #5103 — purely a
**list comprehension** element-type bug, with no matmul or torch involved.
Re-deriving the minimal reproducer on a fresh build (not trusting the earlier
characterisation) was what located the real root cause. Fixed in #5131.
