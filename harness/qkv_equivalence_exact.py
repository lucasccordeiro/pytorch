# EXACT QKV equivalence (scalar-unrolled): fused vs. unfused, proved bit-for-bit.
#
# Same encoding as qkv_equivalence.py, but the equivalence predicate is exact
# element-wise equality (==) instead of torch.allclose's tolerance. This is
# sound here because the fused column is the *identical* multiply-add sequence
# as the unfused projection, so the two are bit-for-bit equal in IEEE-754 — a
# strictly stronger claim than "close within a tolerance".
#
# Run: esbmc qkv_equivalence_exact.py --unwind 8   (expect VERIFICATION SUCCESSFUL)

from stubs import bounded

x00 = bounded(); x01 = bounded(); x10 = bounded(); x11 = bounded()
q00 = bounded(); q01 = bounded(); q10 = bounded(); q11 = bounded()
k00 = bounded(); k01 = bounded(); k10 = bounded(); k11 = bounded()
v00 = bounded(); v01 = bounded(); v10 = bounded(); v11 = bounded()

# Program A: three independent matmuls
Qa00 = x00 * q00 + x01 * q10; Qa01 = x00 * q01 + x01 * q11
Qa10 = x10 * q00 + x11 * q10; Qa11 = x10 * q01 + x11 * q11
Ka00 = x00 * k00 + x01 * k10; Ka01 = x00 * k01 + x01 * k11
Ka10 = x10 * k00 + x11 * k10; Ka11 = x10 * k01 + x11 * k11
Va00 = x00 * v00 + x01 * v10; Va01 = x00 * v01 + x01 * v11
Va10 = x10 * v00 + x11 * v10; Va11 = x10 * v01 + x11 * v11

# Program B: fused weight matrix, one matmul, split the columns
QKV_r0 = [x00 * q00 + x01 * q10, x00 * q01 + x01 * q11,
          x00 * k00 + x01 * k10, x00 * k01 + x01 * k11,
          x00 * v00 + x01 * v10, x00 * v01 + x01 * v11]
QKV_r1 = [x10 * q00 + x11 * q10, x10 * q01 + x11 * q11,
          x10 * k00 + x11 * k10, x10 * k01 + x11 * k11,
          x10 * v00 + x11 * v10, x10 * v01 + x11 * v11]
Qb00 = QKV_r0[0]; Qb01 = QKV_r0[1]; Qb10 = QKV_r1[0]; Qb11 = QKV_r1[1]
Kb00 = QKV_r0[2]; Kb01 = QKV_r0[3]; Kb10 = QKV_r1[2]; Kb11 = QKV_r1[3]
Vb00 = QKV_r0[4]; Vb01 = QKV_r0[5]; Vb10 = QKV_r1[4]; Vb11 = QKV_r1[5]

# Equivalence: exact, bit-for-bit (no tolerance)
assert Qa00 == Qb00; assert Qa01 == Qb01; assert Qa10 == Qb10; assert Qa11 == Qb11
assert Ka00 == Kb00; assert Ka01 == Kb01; assert Ka10 == Kb10; assert Ka11 == Kb11
assert Va00 == Vb00; assert Va01 == Vb01; assert Va10 == Vb10; assert Va11 == Vb11
