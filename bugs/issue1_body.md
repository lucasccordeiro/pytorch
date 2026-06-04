### Summary

The Python list value model returns an **incorrect value** when a numeric matrix element is stored into a nested list inside a function and read back. A trivial 1×1 "matmul" self-identity that must hold by construction is reported `VERIFICATION FAILED`.

This was found while building a small PoC for formally checking equivalence of two PyTorch programs (fused vs. unfused QKV projection) with the Python frontend.

### Minimal reproducer

```python
def mm(A, B):
    C = [[0]]
    s = 0
    s = s + A[0][0] * B[0][0]
    C[0][0] = s
    return C

a = nondet_int(); bb = nondet_int()
__ESBMC_assume(a >= -100); __ESBMC_assume(a <= 100)
__ESBMC_assume(bb >= -100); __ESBMC_assume(bb <= 100)
X = [[a]]; W = [[bb]]
R = mm(X, W)
assert R[0][0] == a * bb       # must hold
```

### Command

```
esbmc bug1_nestedlist_matmul.py --unwind 4
```

### Actual output

```
Violated property:
  file bug1_nestedlist_matmul.py line 30 column 0
  assertion *(signed long int *)return_value$___ESBMC_list_at$1->value == a * bb
VERIFICATION FAILED
```

### Expected

`VERIFICATION SUCCESSFUL` — `R[0][0]` is `0 + a*bb` by construction.

### Notes

The counterexample/violation references `__ESBMC_list_at` and the value model in `src/c2goto/library/python/list.c`. The float variant of the same pattern crashes the SMT backend instead (filed separately). This blocks the natural list/tensor-shaped translation of matmul-style code, forcing scalar unrolling.

### Environment

- ESBMC 8.3.0, 64-bit aarch64 macOS
- Source commit `b4eb5a313f`
