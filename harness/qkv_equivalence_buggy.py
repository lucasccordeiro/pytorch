# BUGGY mutant of qkv_equivalence: the split takes the wrong columns for K
# (it reads Wv's columns {4,5} instead of Wk's {2,3} for row 0), so the fused K
# no longer matches the unfused K. ESBMC must find a counterexample (FAILED).
#
# Run: esbmc qkv_equivalence_buggy.py --unwind 8   (expect VERIFICATION FAILED)

import math
from stubs import bounded

RTOL = 1e-05
ATOL = 1e-08

x00 = bounded(); x01 = bounded(); x10 = bounded(); x11 = bounded()
q00 = bounded(); q01 = bounded(); q10 = bounded(); q11 = bounded()
k00 = bounded(); k01 = bounded(); k10 = bounded(); k11 = bounded()
v00 = bounded(); v01 = bounded(); v10 = bounded(); v11 = bounded()

Qa00 = x00 * q00 + x01 * q10; Qa01 = x00 * q01 + x01 * q11
Qa10 = x10 * q00 + x11 * q10; Qa11 = x10 * q01 + x11 * q11
Ka00 = x00 * k00 + x01 * k10; Ka01 = x00 * k01 + x01 * k11
Ka10 = x10 * k00 + x11 * k10; Ka11 = x10 * k01 + x11 * k11
Va00 = x00 * v00 + x01 * v10; Va01 = x00 * v01 + x01 * v11
Va10 = x10 * v00 + x11 * v10; Va11 = x10 * v01 + x11 * v11

QKV_r0 = [x00 * q00 + x01 * q10, x00 * q01 + x01 * q11,
          x00 * k00 + x01 * k10, x00 * k01 + x01 * k11,
          x00 * v00 + x01 * v10, x00 * v01 + x01 * v11]
QKV_r1 = [x10 * q00 + x11 * q10, x10 * q01 + x11 * q11,
          x10 * k00 + x11 * k10, x10 * k01 + x11 * k11,
          x10 * v00 + x11 * v10, x10 * v01 + x11 * v11]
Qb00 = QKV_r0[0]; Qb01 = QKV_r0[1]; Qb10 = QKV_r1[0]; Qb11 = QKV_r1[1]
Kb00 = QKV_r0[4]; Kb01 = QKV_r0[5]; Kb10 = QKV_r1[2]; Kb11 = QKV_r1[3]  # BUG: K row 0 reads V columns
Vb00 = QKV_r0[4]; Vb01 = QKV_r0[5]; Vb10 = QKV_r1[4]; Vb11 = QKV_r1[5]

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
