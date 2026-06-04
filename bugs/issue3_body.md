### Summary

A user-defined function that **returns a `float`** (here via a ternary), whose argument is itself the result of another user-function call, crashes the SMT backend when the result is used in a floating-point comparison.

Found while modelling `torch.allclose` (an `abs(...) <= atol + rtol*abs(...)` predicate) for a PyTorch-equivalence PoC.

### Minimal reproducer

```python
def myabs(x):
    return x if x >= 0.0 else -x

def b():
    v = nondet_float()
    __ESBMC_assume(v >= -10.0)
    __ESBMC_assume(v <= 10.0)
    return v

a = b()
assert myabs(a) <= 100.0
```

### Command and actual output

Bitwuzla (default):
```
esbmc bug2_userfn_float_compare.py
...
Encoding remaining VCC(s) using bit-vector/floating-point arithmetic
Assertion failed: (r), function to_solver_smt_ast, file smt_ast.h, line 111.
```
(On other small variants the same shape reports `ERROR: Projecting from non-tuple based AST`.)

Z3:
```
esbmc bug2_userfn_float_compare.py --z3
...
Encoding remaining VCC(s) using bit-vector/floating-point arithmetic
Assertion failed: (false), function operator-, file z3++.h, line 1855.
```

### Expected

`VERIFICATION SUCCESSFUL` (`|a| <= 100` holds for `a` bounded to `[-10, 10]`), not a backend crash.

### Notes

Fragile / provenance-dependent: calling the helper on a plain `nondet_float()` (rather than on another function's return value), inlining the ternary, or using `math.fabs` all avoid the crash. Possibly related to the wrong-verdict issue for a user function that returns a *float comparison* (filed separately).

### Environment

- ESBMC 8.3.0, 64-bit aarch64 macOS
- Source commit `b4eb5a313f`
