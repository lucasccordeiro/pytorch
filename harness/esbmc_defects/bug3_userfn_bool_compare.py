# ESBMC Python-frontend defect #3: a user-defined function that *returns the
# result of a floating-point comparison* (a bool) produces a WRONG verdict.
#
# Here a == c by construction, so allclose1(a, c) is trivially True and the
# assertion must hold. ESBMC reports:
#   esbmc bug3_userfn_bool_compare.py  -> VERIFICATION FAILED   (incorrect)
#
# The SAME predicate inlined at the assertion verifies SUCCESSFUL:
#   assert math.fabs(a - c) <= 1e-08 + 1e-05 * math.fabs(c)   -> SUCCESSFUL
#
# Likely the same root cause as bug2_userfn_float_compare.py (mishandling of a
# user function whose return value is derived from FP operands); there it
# crashes when the return type is float, here it returns a wrong bool.
# Consequence for users: tolerance/allclose predicates must be inlined, not
# factored into a helper -- which is what qkv_equiv.py does.

import math


def allclose1(a, c):
    return math.fabs(a - c) <= 1e-08 + 1e-05 * math.fabs(c)


def b():
    v = nondet_float()
    __ESBMC_assume(v >= -10.0)
    __ESBMC_assume(v <= 10.0)
    return v


p = b()
q = b()
a = p * q
c = p * q
assert allclose1(a, c)      # must hold (a == c); ESBMC reports FAILED
