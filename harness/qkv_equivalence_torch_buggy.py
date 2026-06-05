# BUGGY mutant of qkv_equivalence_torch: the split swaps the K and V columns,
# so the fused K and V no longer match the unfused projections. ESBMC must find
# a counterexample (expect VERIFICATION FAILED).

import torch
from stubs import bounded

S = 1
D = 2
H = 1

X = [[bounded() for _ in range(D)] for _ in range(S)]
Wq = [[bounded() for _ in range(H)] for _ in range(D)]
Wk = [[bounded() for _ in range(H)] for _ in range(D)]
Wv = [[bounded() for _ in range(H)] for _ in range(D)]

Qa = torch.mm(X, Wq)
Ka = torch.mm(X, Wk)
Va = torch.mm(X, Wv)

Wc = [[0.0 for _ in range(3 * H)] for _ in range(D)]
r = 0
while r < D:
    c = 0
    while c < H:
        wqr = Wq[r]
        wkr = Wk[r]
        wvr = Wv[r]
        Wc[r][c] = wqr[c]
        Wc[r][H + c] = wkr[c]
        Wc[r][2 * H + c] = wvr[c]
        c = c + 1
    r = r + 1

QKV = torch.mm(X, Wc)

Qb = [[0.0 for _ in range(H)] for _ in range(S)]
Kb = [[0.0 for _ in range(H)] for _ in range(S)]
Vb = [[0.0 for _ in range(H)] for _ in range(S)]
i = 0
while i < S:
    c = 0
    while c < H:
        qkvr = QKV[i]
        Qb[i][c] = qkvr[c]
        Kb[i][c] = qkvr[2 * H + c]  # BUG: K reads the V column
        Vb[i][c] = qkvr[H + c]  # BUG: V reads the K column
        c = c + 1
    i = i + 1

assert torch.allclose(Qa, Qb)
assert torch.allclose(Ka, Kb)
assert torch.allclose(Va, Vb)
