# AUDIT — ESBMC defects surfaced by this PoC

Driving the QKV equivalence proof through ESBMC's Python frontend exposed a
chain of defects in the list value/type model and the float encoding. This is
the ledger; minimal reproducers live under
[`harness/esbmc_defects/`](./harness/esbmc_defects/).

All issue/PR numbers are on [github.com/esbmc/esbmc](https://github.com/esbmc/esbmc).

## Fixed upstream

| # | Title | Repro | Fix |
| --- | --- | --- | --- |
| [#5102](https://github.com/esbmc/esbmc/issues/5102) | Nested-list matmul returns wrong value (list value model) | `esbmc_defects/bug1_nestedlist_matmul.py` | [#5111](https://github.com/esbmc/esbmc/pull/5111) + [#5113](https://github.com/esbmc/esbmc/pull/5113) |
| [#5103](https://github.com/esbmc/esbmc/issues/5103) | Float matmul over nested lists crashes SMT backend (`smt_sort.h:123` / Z3 `rm and fp sorts`) | `esbmc_defects/bug1b_nestedlist_float_crash.py` | [#5111](https://github.com/esbmc/esbmc/pull/5111) |
| [#5104](https://github.com/esbmc/esbmc/issues/5104) | User function returning a float crashes SMT backend in FP comparison (`smt_ast.h:111`) | `esbmc_defects/bug2_userfn_float_compare.py` | closed |
| [#5105](https://github.com/esbmc/esbmc/issues/5105) | User function returning a float comparison yields wrong verdict (FAILED vs SUCCESSFUL) | `esbmc_defects/bug3_userfn_bool_compare.py` | closed |
| [#5129](https://github.com/esbmc/esbmc/issues/5129) | FP arithmetic over a comprehension-built nested-list float element crashes SMT backend (`smt_sort.h:123` / Z3 `rm and fp sorts`) — residual of #5103 | reproduced by `qkv_equivalence_torch` pre-fix | [#5131](https://github.com/esbmc/esbmc/pull/5131) |

The two `#5111`/`#5113` fixes are what made nested-list matmul usable at all;
they are the precondition for the torch operational model.

## Open

| # | Title | Notes |
| --- | --- | --- |
| [#5115](https://github.com/esbmc/esbmc/issues/5115) | `numpy.matmul`/`dot` on symbolic inputs: array-bounds violation in `linalg.c` `dot` (+ int64-only) | blocks a numpy-backed matmul path; torch OM is float-typed instead |
| [#5116](https://github.com/esbmc/esbmc/issues/5116) | SIGABRT during SMT encoding on nested-list matmul (`byte_extract` over dynamic list arrays) | comp-built wide list filled with computed offsets then matmul'd |
| [#5121](https://github.com/esbmc/esbmc/issues/5121) | Nested-list (2D/3D tensor) construction & deep access too slow to verify (`cat`/`split` don't converge) | why this PoC uses manual column indexing, not `torch.cat`/`split` |
| [#5122](https://github.com/esbmc/esbmc/issues/5122) | SIGABRT (`json.hpp:2174`) on arithmetic with a double-subscript of a nested list (`M[i][j] - x`) | fires at parse time on any binop with a double-subscript operand; sidestep by row-extracting first (`r = M[i]; r[j]`) |

## This PoC's own fix — #5129 (fixed by #5131, merged)

A nested list **comprehension** `[[0.0 for _ in range(N)] for _ in range(M)]`
records a single homogeneous entry in `list_type_map`.
`python_list::handle_index_access` gated the nested-element type-resolution
block on `index < size`, so a constant outer index `>= 1` skipped it, the inner
`float` type was lost, and `C[1][0]` used in FP arithmetic reached the SMT FP
encoder with a non-FP sort. [#5131](https://github.com/esbmc/esbmc/pull/5131)
widens the guard and clamps the type lookup to the homogeneous entry (the
runtime value is still read at the real index). Without #5131,
`qkv_equivalence_torch` aborts; with it, it verifies. `C[0][0]`, `==`
comparison, and integer matrices were unaffected — which is why the bug hid
until FP arithmetic over a matmul result at row `>= 1`. The PoC found, root-
caused, fixed, and regression-tested it.
