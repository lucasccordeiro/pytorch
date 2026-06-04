# ESBMC defect #1 (float variant): list-of-floats matmul crashes the SMT
# backend instead of returning a verdict.
#   esbmc bug1b_nestedlist_float_crash.py --unwind 4
#     Bitwuzla: Assertion failed (id==SMT_SORT_BVFP||id==SMT_SORT_FPBV),
#               get_exponent_width, smt_sort.h:123
#     Z3 (--z3): ERROR: Z3 error rm and fp sorts expected
# Same root cause as bug1_nestedlist_matmul.py (Python list value model), but
# surfaces as a solver-layer crash once floats flow through the list buffer.

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
