### Summary

A floating-point matmul over **nested lists** crashes the SMT backend (assertion failure under Bitwuzla, hard error under Z3) instead of producing a verdict.

Found while building a PoC for formal equivalence checking of two PyTorch programs with the Python frontend. This is the floating-point counterpart of the nested-list integer wrong-value bug (filed separately) — same code shape, but it manifests as a solver-layer crash once floats flow through the list buffer.

### Minimal reproducer

```python
S = 1
D = 1
H = 1

def mm(A, B, n, k, m):
    C = [[0.0 for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for j in range(m):
            s = 0.0
            for t in range(k):
                s = s + A[i][t] * B[t][j]
            C[i][j] = s
    return C

def bounded():
    v = nondet_float()
    __ESBMC_assume(v >= -10.0)
    __ESBMC_assume(v <= 10.0)
    return v

X  = [[bounded() for _ in range(D)] for _ in range(S)]
Wq = [[bounded() for _ in range(H)] for _ in range(D)]
Wk = [[bounded() for _ in range(H)] for _ in range(D)]
Wv = [[bounded() for _ in range(H)] for _ in range(D)]

Qa = mm(X, Wq, S, D, H)
Ka = mm(X, Wk, S, D, H)
Va = mm(X, Wv, S, D, H)

Wc = [[0.0 for _ in range(3*H)] for _ in range(D)]
for r in range(D):
    for c in range(H):
        Wc[r][c]       = Wq[r][c]
        Wc[r][H + c]   = Wk[r][c]
        Wc[r][2*H + c] = Wv[r][c]
QKV = mm(X, Wc, S, D, 3*H)
Qb = [[QKV[i][c]       for c in range(H)] for i in range(S)]
Kb = [[QKV[i][H + c]   for c in range(H)] for i in range(S)]
Vb = [[QKV[i][2*H + c] for c in range(H)] for i in range(S)]

for i in range(S):
    for c in range(H):
        assert Qa[i][c] == Qb[i][c]
        assert Ka[i][c] == Kb[i][c]
        assert Va[i][c] == Vb[i][c]
```

### Commands and actual output

Bitwuzla (default):
```
esbmc bug1b_nestedlist_float_crash.py --unwind 4
...
Encoding remaining VCC(s) using bit-vector/floating-point arithmetic
Assertion failed: (id == SMT_SORT_BVFP || id == SMT_SORT_FPBV), function get_exponent_width, file smt_sort.h, line 123.
```

Z3:
```
esbmc bug1b_nestedlist_float_crash.py --unwind 4 --z3
...
Encoding remaining VCC(s) using bit-vector/floating-point arithmetic
ERROR: Z3 error rm and fp sorts expected encountered
```

### Expected

A normal `VERIFICATION SUCCESSFUL` / `FAILED` verdict, not a backend crash. (The algebra is an identity, so the expected verdict is `SUCCESSFUL`.)

### Notes

Likely the same root cause as the nested-list integer wrong-value issue (the `float_buf`/`float_idx` indirection in `src/c2goto/library/python/list.c`): a list element whose stored sort is not the expected FP sort reaches `get_exponent_width`.

### Environment

- ESBMC 8.3.0, 64-bit aarch64 macOS
- Source commit `b4eb5a313f`
