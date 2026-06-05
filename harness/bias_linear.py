# Bias-fused linear equivalence (S=1, D=2, H=1), via ESBMC's torch OM.
#
#   A (unfused): Y = X @ W ; Y = Y + b     (matmul, then broadcast bias add)
#   B (fused):   Xa = [X | 1] ; Wa = [W ; b] ; Y = Xa @ Wa
#
# The augmented matmul folds the bias into one matmul: the extra unit column of
# Xa times the bias row of Wa contributes exactly b[j] as the final
# accumulation term, so A and B perform the same FP operations in the same order
# and are FP-exactly equal. The bias add in A is done in user code (single
# subscripts after a row-extract, to avoid the double-subscript parse crash
# esbmc#5122); the matmuls and the equivalence check go through the torch OM.
#
# Run: esbmc bias_linear.py --unwind 4   (expect VERIFICATION SUCCESSFUL)

import torch
from stubs import bounded

S = 1
D = 2
H = 1

X = [[bounded() for _ in range(D)] for _ in range(S)]
W = [[bounded() for _ in range(H)] for _ in range(D)]
b = [bounded() for _ in range(H)]

# --- A: unfused matmul + broadcast bias add ---
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

# --- B: augment X with a unit column and W with the bias row, one matmul ---
Xa = [[0.0 for _ in range(D + 1)] for _ in range(S)]
i = 0
while i < S:
    xr = X[i]
    d = 0
    while d < D:
        Xa[i][d] = xr[d]
        d = d + 1
    Xa[i][D] = 1.0
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
