# Torch-native QKV equivalence: fused vs. unfused projections, proved with
# ESBMC's torch operational model (torch.mm + torch.allclose, PR esbmc#5120)
# plus the nested-list element-type fix (PR esbmc#5131, Fixes esbmc#5129).
#
# Unfused (A):  Q = X @ Wq ; K = X @ Wk ; V = X @ Wv      (three torch.mm)
# Fused   (B):  Wc = [Wq | Wk | Wv] ; QKV = X @ Wc ; split QKV back into Q,K,V
#
# The matmuls and the equivalence check go through the torch operational
# model. The concat (building Wc) and split (slicing QKV) are done by manual
# column assignment rather than torch.cat / torch.split, which are correct in
# the model but unwinding-heavy (a 1x1x3 cat+split alone takes ~2.5 min);
# manual indexing keeps the proof tractable. Inputs are bounded nondet floats,
# so the result holds for ALL admissible inputs, not one random sample.
#
# Dims kept small (S=1, D=2, H=1) so the four matmuls stay within a few minutes.
# Run: esbmc qkv_equivalence_torch.py --unwind 4   (expect VERIFICATION SUCCESSFUL)

import torch
from stubs import bounded

S = 1
D = 2
H = 1

X = [[bounded() for _ in range(D)] for _ in range(S)]
Wq = [[bounded() for _ in range(H)] for _ in range(D)]
Wk = [[bounded() for _ in range(H)] for _ in range(D)]
Wv = [[bounded() for _ in range(H)] for _ in range(D)]

# --- Program A: three independent projections via torch.mm ---
Qa = torch.mm(X, Wq)
Ka = torch.mm(X, Wk)
Va = torch.mm(X, Wv)

# --- Program B: fuse the weights, one matmul, then split the columns back ---
# Build Wc = [Wq | Wk | Wv] (D x 3H) by column assignment.
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

# split(dim=1): Q = cols[0:H], K = cols[H:2H], V = cols[2H:3H]
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

# --- equivalence: torch.allclose(A, B) for each of Q, K, V ---
assert torch.allclose(Qa, Qb)
assert torch.allclose(Ka, Kb)
assert torch.allclose(Va, Vb)
