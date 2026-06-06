#!/usr/bin/env python3
"""Differential test: ESBMC's torch operational model vs. real PyTorch.

The PoC's soundness is "modulo the operational model = real PyTorch". This script
turns that disclaimer into *evidence*: it runs the OM's reference implementations
(mm / matmul / cat / split / allclose, copied verbatim from
`src/python-frontend/models/torch.py` in ESBMC) against real `torch` on many
random inputs and checks they agree.

Everything is done in **float64** (torch's default is float32; Python floats are
doubles) so the comparison is apples-to-apples for the IEEE-754 semantics the OM
models. Inputs use the same bounded range as the harnesses ([-10, 10]).

Run (needs PyTorch):  python3 validation/om_differential_test.py
"""

from __future__ import annotations
import math
import random
import sys

import torch

torch.set_default_dtype(torch.float64)

# --------------------------------------------------------------------------
# OM reference implementations — verbatim semantics of ESBMC's models/torch.py
# (rewritten with for-loops; arithmetic and order are identical).
# --------------------------------------------------------------------------

def om_mm(A, B):
    n, k, m = len(A), len(B), len(B[0])
    C = [[0.0 for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for j in range(m):
            s = 0.0
            for t in range(k):
                s = s + A[i][t] * B[t][j]
            C[i][j] = s
    return C


def om_cat(tensors, dim):  # dim == 1 (columns)
    n = len(tensors[0])
    total = sum(len(t[0]) for t in tensors)
    out = [[0.0 for _ in range(total)] for _ in range(n)]
    for r in range(n):
        col = 0
        for t in tensors:
            for c in range(len(t[r])):
                out[r][col] = t[r][c]
                col += 1
    return out


def om_split(tensor, sizes, dim):  # dim == 1 (columns)
    parts, start = [], 0
    for width in sizes:
        n = len(tensor)
        chunk = [[0.0 for _ in range(width)] for _ in range(n)]
        for r in range(n):
            for c in range(width):
                chunk[r][c] = tensor[r][start + c]
        parts.append(chunk)
        start += width
    return parts


def om_allclose(a, b, rtol=1e-05, atol=1e-08):
    for i in range(len(a)):
        for j in range(len(a[i])):
            if math.fabs(a[i][j] - b[i][j]) > atol + rtol * math.fabs(b[i][j]):
                return False
    return True


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def rnd_mat(n, m):
    return [[random.uniform(-10.0, 10.0) for _ in range(m)] for _ in range(n)]


def flat(t):  # list-of-lists -> flat list
    return [v for row in t for v in row]


# --------------------------------------------------------------------------
# Differential checks
# --------------------------------------------------------------------------

def check_mm(trials=2000):
    exact = within_tol = 0
    max_rel = 0.0
    for _ in range(trials):
        n = random.randint(1, 4)
        k = random.randint(1, 6)
        m = random.randint(1, 4)
        A, B = rnd_mat(n, k), rnd_mat(k, m)
        ref = flat(om_mm(A, B))
        got = flat(torch.mm(torch.tensor(A), torch.tensor(B)).tolist())
        if ref == got:
            exact += 1
        # faithfulness = agreement up to IEEE-754 rounding (torch.allclose defaults)
        if all(math.fabs(a - b) <= 1e-8 + 1e-5 * math.fabs(b) for a, b in zip(ref, got)):
            within_tol += 1
        for a, b in zip(ref, got):
            denom = max(math.fabs(b), 1e-300)
            max_rel = max(max_rel, math.fabs(a - b) / denom)
    return exact, within_tol, trials, max_rel


def check_cat_split(trials=2000):
    ok = 0
    for _ in range(trials):
        n = random.randint(1, 4)
        widths = [random.randint(1, 4) for _ in range(3)]
        mats = [rnd_mat(n, w) for w in widths]
        ref_cat = om_cat(mats, 1)
        got_cat = torch.cat([torch.tensor(t) for t in mats], dim=1).tolist()
        ref_parts = om_split(ref_cat, widths, 1)
        got_parts = [p.tolist() for p in torch.split(torch.tensor(got_cat), widths, dim=1)]
        if ref_cat == got_cat and ref_parts == got_parts:
            ok += 1
    return ok, trials


def check_allclose(trials=4000):
    agree = 0
    for _ in range(trials):
        n, m = random.randint(1, 4), random.randint(1, 4)
        a = rnd_mat(n, m)
        # Sometimes equal, sometimes perturbed near/over the tolerance.
        b = [row[:] for row in a]
        if random.random() < 0.6:
            for i in range(n):
                for j in range(m):
                    scale = random.choice([1e-9, 1e-6, 1e-4, 1e-2])
                    b[i][j] += random.uniform(-scale, scale)
        ref = om_allclose(a, b)
        got = bool(torch.allclose(torch.tensor(a), torch.tensor(b)))  # rtol/atol defaults
        if ref == got:
            agree += 1
    return agree, trials


def main() -> int:
    random.seed(20260606)
    print(f"PyTorch {torch.__version__}, dtype={torch.get_default_dtype()}\n")

    e, w, t, mr = check_mm()
    print(f"mm        : {w}/{t} agree with torch.mm within IEEE-754 tolerance "
          f"(of which {e}/{t} bit-exact); max relative error {mr:.2e}")

    ok, t2 = check_cat_split()
    print(f"cat/split : {ok}/{t2} bit-exact vs torch.cat/torch.split")

    ag, t3 = check_allclose()
    print(f"allclose  : {ag}/{t3} same verdict as torch.allclose")

    # Faithfulness criterion: data-movement ops (cat/split) and the allclose
    # predicate must match EXACTLY; mm must match torch up to IEEE-754 rounding
    # (it is NOT bit-exact, because torch.mm uses a different reduction order than
    # the OM's sequential sum — see note below).
    ok_all = (w == t) and (ok == t2) and (ag == t3)
    print("\n" + ("PASS" if ok_all else "FAIL")
          + "  — OM is a faithful reference: cat/split/allclose exact; "
          + "mm agrees with torch up to rounding.")
    print("Note: mm is not *bit*-identical to torch.mm (different reduction order); "
          "the PoC proves unfused == fused WITHIN the OM's sequential order.")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
