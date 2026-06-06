# A REASSOCIATING fusion that is sound over the reals but UNSOUND in IEEE-754.
#
# Reference (left-associated) vs an "optimised" reassociated reduction of the same
# dot product. Over ℝ these are equal; in bit-precise floating point they are not
# (FP addition is not associative). ESBMC `--floatbv` therefore REFUTES the exact
# equality and returns a concrete counterexample — the bug-finding case that
# motivates bounded model checking (and that an interactive prover over reals, or
# ESBMC `--ir`, cannot expose). Expect: VERIFICATION FAILED (+ counterexample).
#
# This is the contrast case to the order-preserving QKV proofs: there the fused
# form keeps the same operation order (provable); here the "optimisation" reorders
# the additions, so it is only correct up to rounding (see reassoc_fusion_tol.py).
#
# Run: esbmc reassoc_fusion_exact.py --unwind 2   (expect VERIFICATION FAILED)

from stubs import bounded

x0 = bounded(); x1 = bounded(); x2 = bounded()
w0 = bounded(); w1 = bounded(); w2 = bounded()

p0 = x0 * w0
p1 = x1 * w1
p2 = x2 * w2

ref = (p0 + p1) + p2     # reference reduction order
opt = p0 + (p1 + p2)     # reassociated "optimisation"

assert ref == opt        # exact: FALSE in IEEE-754 for some bounded inputs
