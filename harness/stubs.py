# Shared helpers for the ESBMC PyTorch verification harnesses.
#
# Imported by the harness entry scripts as `from stubs import bounded`.
# ESBMC's Python frontend resolves the import relative to the harness
# directory, so no packaging or PYTHONPATH setup is required.


def bounded() -> float:
    # Bounded nondeterministic float. The bound is mandatory: it excludes
    # NaN/Inf, for which the equality / closeness predicates behave
    # non-intuitively (NaN != NaN would spuriously fail an `==` proof, and
    # Inf - Inf = NaN would break the tolerance predicate). Constraining each
    # input to [-10, 10] keeps the proof over a finite, well-behaved range
    # while remaining symbolic across that whole range.
    v = nondet_float()
    __ESBMC_assume(v >= -10.0)
    __ESBMC_assume(v <= 10.0)
    return v
