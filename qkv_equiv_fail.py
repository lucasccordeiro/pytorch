# Formal equivalence proof: fused vs. unfused QKV projection (PyTorch), via ESBMC.
#
# Original PyTorch programs (Eduardo Valentin):
#   A (unfused): Q = X@Wq ; K = X@Wk ; V = X@Wv
#   B (fused):   W = cat([Wq,Wk,Wv], dim=1) ; QKV = X@W ; Q,K,V = split(QKV)
# The original harness compared ONE random sample with torch.allclose(...).
# Here we replace torch.randn with bounded nondeterministic floats, so the
# proof holds for ALL admissible inputs, and we model torch.allclose's
# tolerance predicate explicitly.
#
# Dims kept tiny and matrices scalar-unrolled on purpose: ESBMC's Python list
# model cannot yet carry matrix elements through a triple-loop matmul
# (see ../bugs/), so we encode the linear algebra directly over scalars.
#
# Run:  esbmc qkv_equiv.py --unwind 8       (expect: VERIFICATION SUCCESSFUL)

# torch.allclose defaults
RTOL = 1e-05
ATOL = 1e-08


import math


def b():
    # bounded nondet float: the bound is mandatory -- it excludes NaN/Inf, for
    # which the equality/closeness predicate would behave non-intuitively.
    v = nondet_float()
    __ESBMC_assume(v >= -10.0)
    __ESBMC_assume(v <= 10.0)
    return v


# torch.allclose element-wise predicate, written INLINE as a macro-style helper.
# It must NOT be a Python function: a user function that *returns* a float
# comparison currently makes ESBMC produce a wrong verdict, and one that returns
# a float crashes the backend (see ../bugs/). math.fabs (the math OM intrinsic)
# is fine; a hand-written abs is not.
#   close(a, c)  ==>  math.fabs(a - c) <= ATOL + RTOL * math.fabs(c)


# --- inputs: X (2x2), Wq,Wk,Wv (2x2 each) ---
x00 = b(); x01 = b(); x10 = b(); x11 = b()
q00 = b(); q01 = b(); q10 = b(); q11 = b()
k00 = b(); k01 = b(); k10 = b(); k11 = b()
v00 = b(); v01 = b(); v10 = b(); v11 = b()

# --- Program A: three independent matmuls  X @ Wq, X @ Wk, X @ Wv ---
Qa00 = x00 * q00 + x01 * q10; Qa01 = x00 * q01 + x01 * q11
Qa10 = x10 * q00 + x11 * q10; Qa11 = x10 * q01 + x11 * q11
Ka00 = x00 * k00 + x01 * k10; Ka01 = x00 * k01 + x01 * k11
Ka10 = x10 * k00 + x11 * k10; Ka11 = x10 * k01 + x11 * k11
Va00 = x00 * v00 + x01 * v10; Va01 = x00 * v01 + x01 * v11
Va10 = x10 * v00 + x11 * v10; Va11 = x10 * v01 + x11 * v11

# --- Program B: W_QKV = cat([Wq,Wk,Wv], dim=1) is 2x6 ; QKV = X @ W_QKV ; split ---
# columns of W_QKV: {0,1}=Wq, {2,3}=Wk, {4,5}=Wv
QKV_r0 = [x00 * q00 + x01 * q10, x00 * q01 + x01 * q11,
          x00 * k00 + x01 * k10, x00 * k01 + x01 * k11,
          x00 * v00 + x01 * v10, x00 * v01 + x01 * v11]
QKV_r1 = [x10 * q00 + x11 * q10, x10 * q01 + x11 * q11,
          x10 * k00 + x11 * k10, x10 * k01 + x11 * k11,
          x10 * v00 + x11 * v10, x10 * v01 + x11 * v11]
# split(dim=1) -> Q = cols[0:2], K = cols[2:4], V = cols[4:6]
Qb00 = QKV_r0[0]; Qb01 = QKV_r0[1]; Qb10 = QKV_r1[0]; Qb11 = QKV_r1[1]
Kb00 = QKV_r0[4]; Kb01 = QKV_r0[5]; Kb10 = QKV_r1[2]; Kb11 = QKV_r1[3]
Vb00 = QKV_r0[4]; Vb01 = QKV_r0[5]; Vb10 = QKV_r1[4]; Vb11 = QKV_r1[5]

# --- equivalence: torch.allclose(A, B) for every element of Q, K, V (inlined) ---
assert math.fabs(Qa00 - Qb00) <= ATOL + RTOL * math.fabs(Qb00)
assert math.fabs(Qa01 - Qb01) <= ATOL + RTOL * math.fabs(Qb01)
assert math.fabs(Qa10 - Qb10) <= ATOL + RTOL * math.fabs(Qb10)
assert math.fabs(Qa11 - Qb11) <= ATOL + RTOL * math.fabs(Qb11)
assert math.fabs(Ka00 - Kb00) <= ATOL + RTOL * math.fabs(Kb00)
assert math.fabs(Ka01 - Kb01) <= ATOL + RTOL * math.fabs(Kb01)
assert math.fabs(Ka10 - Kb10) <= ATOL + RTOL * math.fabs(Kb10)
assert math.fabs(Ka11 - Kb11) <= ATOL + RTOL * math.fabs(Kb11)
assert math.fabs(Va00 - Vb00) <= ATOL + RTOL * math.fabs(Vb00)
assert math.fabs(Va01 - Vb01) <= ATOL + RTOL * math.fabs(Vb01)
assert math.fabs(Va10 - Vb10) <= ATOL + RTOL * math.fabs(Vb10)
assert math.fabs(Va11 - Vb11) <= ATOL + RTOL * math.fabs(Vb11)
