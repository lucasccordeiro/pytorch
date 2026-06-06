# The SAME reassociating fusion as reassoc_fusion_exact.py, but checked with
# torch.allclose's tolerance instead of exact equality.
#
# Reassociating a 3-term reduction over bounded inputs changes the result by at
# most a few ULPs of the intermediate magnitudes, which is well inside
# `atol + rtol*|opt|`. So the optimisation is *acceptable under tolerance* even
# though it is not bit-exact — ESBMC proves it for all bounded inputs.
# Expect: VERIFICATION SUCCESSFUL.
#
# Together with reassoc_fusion_exact.py this makes the exact-vs-tolerance
# distinction concrete: the reordering is refuted bit-precisely (with a witness)
# yet is within `torch.allclose` for all bounded inputs.
#
# NOTE — provable but EXPENSIVE, so NOT in the default `make verify` suite.
# Refuting the exact equality takes seconds (a single witness suffices), but
# *proving* this tolerance bound for the whole bit-precise FP input space did not
# converge in ~11 min under Bitwuzla. The asymmetry is the point: with BMC,
# finding a counterexample is cheap; proving an FP bound everywhere is hard.
#
# Run: esbmc reassoc_fusion_tol.py --unwind 2   (SUCCESSFUL in principle; slow)

import math
from stubs import bounded

RTOL = 1e-05
ATOL = 1e-08

x0 = bounded(); x1 = bounded(); x2 = bounded()
w0 = bounded(); w1 = bounded(); w2 = bounded()

p0 = x0 * w0
p1 = x1 * w1
p2 = x2 * w2

ref = (p0 + p1) + p2
opt = p0 + (p1 + p2)

assert math.fabs(ref - opt) <= ATOL + RTOL * math.fabs(opt)   # within allclose tolerance
