# ESBMC Python-frontend defect #1: nested-list numeric storage returns wrong
# values, and crashes the FP solver backend for floats.
#
# Symptom (integers): the matmul self-identity below FAILS even though
#   R[0][0] == a*b  must hold by construction.
#   => esbmc bug1_nestedlist_matmul.py  -> VERIFICATION FAILED (wrong value)
#
# Symptom (floats): replacing the ints with bounded nondet_float() and a
# [[0.0 for _ in range(m)] for _ in range(n)] result buffer crashes Bitwuzla:
#   Assertion failed: (id == SMT_SORT_BVFP || id == SMT_SORT_FPBV),
#   function get_exponent_width, file smt_sort.h, line 123
# and Z3: "ERROR: Z3 error rm and fp sorts expected".
#
# Root cause appears to be the list value model in
# src/c2goto/library/python/list.c (float_buf / float_idx indirection in
# __ESBMC_list_push / __ESBMC_copy_value); the counterexample trace points there.

def mm(A, B):
    C = [[0]]
    s = 0
    s = s + A[0][0] * B[0][0]
    C[0][0] = s
    return C

a = nondet_int(); bb = nondet_int()
__ESBMC_assume(a >= -100); __ESBMC_assume(a <= 100)
__ESBMC_assume(bb >= -100); __ESBMC_assume(bb <= 100)
X = [[a]]; W = [[bb]]
R = mm(X, W)
assert R[0][0] == a * bb       # must hold; ESBMC reports FAILED
