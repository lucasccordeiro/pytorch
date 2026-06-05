# BUGGY mutant of bias_linear: the fused augmentation uses a 0.0 column instead
# of a unit column, so the bias is never applied (Yb = X @ W, missing + b). The
# unfused A still adds b, so the two disagree wherever b != 0 -- ESBMC must find
# a counterexample (expect VERIFICATION FAILED).

import torch
from stubs import bounded

S = 1
D = 2
H = 1

X = [[bounded() for _ in range(D)] for _ in range(S)]
W = [[bounded() for _ in range(H)] for _ in range(D)]
b = [bounded() for _ in range(H)]

P = torch.mm(X, W)
Ya = [[0.0 for _ in range(H)] for _ in range(S)]
i = 0
while i < S:
    pr = P[i]
    j = 0
    while j < H:
        Ya[i][j] = pr[j] + b[j]
        j = j + 1
    i = i + 1

Xa = [[0.0 for _ in range(D + 1)] for _ in range(S)]
i = 0
while i < S:
    xr = X[i]
    d = 0
    while d < D:
        Xa[i][d] = xr[d]
        d = d + 1
    Xa[i][D] = 0.0  # BUG: should be 1.0; with 0.0 the bias row is never added
    i = i + 1

Wa = [[0.0 for _ in range(H)] for _ in range(D + 1)]
d = 0
while d < D:
    wr = W[d]
    j = 0
    while j < H:
        Wa[d][j] = wr[j]
        j = j + 1
    d = d + 1
j = 0
while j < H:
    Wa[D][j] = b[j]
    j = j + 1

Yb = torch.mm(Xa, Wa)

assert torch.allclose(Ya, Yb)
