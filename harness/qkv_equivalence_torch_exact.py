# EXACT torch-native QKV equivalence: fused vs. unfused, proved bit-for-bit.
#
# Same as qkv_equivalence_torch.py, but torch.allclose is called with zero
# tolerance (rtol=0, atol=0), so it reduces to element-wise == — a bit-for-bit
# equality proof rather than a tolerance check. Sound here because the fused
# column is the identical multiply-add sequence as the unfused projection.
#
# Run: esbmc qkv_equivalence_torch_exact.py --unwind 4   (expect SUCCESSFUL)

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
        Kb[i][c] = qkvr[H + c]
        Vb[i][c] = qkvr[2 * H + c]
        c = c + 1
    i = i + 1

# Zero tolerance => bit-for-bit equality (allclose reduces to element-wise ==)
assert torch.allclose(Qa, Qb, 0.0, 0.0)
assert torch.allclose(Ka, Kb, 0.0, 0.0)
assert torch.allclose(Va, Vb, 0.0, 0.0)
