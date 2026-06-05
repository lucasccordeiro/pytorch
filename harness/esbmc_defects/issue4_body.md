### Summary

A user-defined function that **returns the result of a floating-point comparison** (i.e. a `bool` computed from `float` operands) produces a **wrong verdict**: an assertion that must hold is reported `VERIFICATION FAILED`. Inlining the identical predicate at the assertion site verifies `SUCCESSFUL`.

Found while modelling `torch.allclose` for a PyTorch-equivalence PoC.

### Minimal reproducer

```python
import math


def allclose1(a, c):
    return math.fabs(a - c) <= 1e-08 + 1e-05 * math.fabs(c)


def b():
    v = nondet_float()
    __ESBMC_assume(v >= -10.0)
    __ESBMC_assume(v <= 10.0)
    return v


p = b()
q = b()
a = p * q
c = p * q
assert allclose1(a, c)      # must hold (a == c)
```

### Command and actual output

```
esbmc bug3_userfn_bool_compare.py
...
Violated property:
  file bug3_userfn_bool_compare.py line 35 column 0
  assertion (signed int)py:bug3_userfn_bool_compare.py@__assert_temp == 1
VERIFICATION FAILED
```

### Expected

`VERIFICATION SUCCESSFUL`. Since `a` and `c` are the same expression, `a == c`, so `math.fabs(a-c) == 0.0 <= 1e-08 + 1e-05*math.fabs(c)`.

The same predicate inlined verifies correctly:
```python
assert math.fabs(a - c) <= 1e-08 + 1e-05 * math.fabs(c)   # -> VERIFICATION SUCCESSFUL
```

### Notes

Likely the same root cause as the crash for a user function returning a `float` used in an FP comparison (filed separately) — here the return type is `bool` (an FP comparison) and the symptom is a silent wrong verdict rather than a crash. Wrong-verdict bugs are especially dangerous because they are not visible as errors. Workaround: inline tolerance/`allclose`-style predicates instead of factoring them into helper functions.

### Environment

- ESBMC 8.3.0, 64-bit aarch64 macOS
- Source commit `b4eb5a313f`
