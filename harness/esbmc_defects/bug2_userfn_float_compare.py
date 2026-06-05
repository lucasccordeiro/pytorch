# ESBMC Python-frontend defect #2: a user-defined float-returning function,
# whose argument is itself the result of another user-function call, crashes
# the SMT backend when its result is used in a floating-point comparison.
#
#   esbmc bug2_userfn_float_compare.py
#     Bitwuzla: ERROR: Projecting from non-tuple based AST   (or)
#               Assertion failed: (r), to_solver_smt_ast, smt_ast.h:111
#     Z3 (--z3): Assertion failed: (false), operator-, z3++.h:1855
#
# Note the fragility: inlining the ternary, or using math.fabs, or calling the
# helper on a plain nondet_float() (rather than on b()'s return), avoids the
# crash -- which is why the PoC uses math.fabs for its tolerance predicate.

def myabs(x):
    return x if x >= 0.0 else -x

def b():
    v = nondet_float()
    __ESBMC_assume(v >= -10.0)
    __ESBMC_assume(v <= 10.0)
    return v

a = b()
assert myabs(a) <= 100.0
