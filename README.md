# Formal equivalence checking of two PyTorch programs with ESBMC — PoC

Proof of concept for proving that two PyTorch programs compute the same result,
using the [ESBMC](https://github.com/esbmc/esbmc) bounded model checker's Python
frontend.

## The example

A self-attention QKV projection written two ways.

- **Program A (unfused)** — three independent matmuls:
  `Q = X @ Wq`, `K = X @ Wk`, `V = X @ Wv`.
- **Program B (fused)** — concatenate the weights, one matmul, then split:
  `W = cat([Wq, Wk, Wv], dim=1)`, `QKV = X @ W`, `Q, K, V = split(QKV)`.

The original script compared **one random sample** with `torch.allclose(...)` and
printed whether they matched. This PoC turns that runtime spot-check into a
**formal proof over all admissible inputs**.

## Approach

1. **Inputs become symbolic.** `torch.randn(...)` → bounded `nondet_float()`,
   with `__ESBMC_assume(-10.0 <= v <= 10.0)` per element. ESBMC then explores
   *every* input in that range, not one sample.
   - The bound is **mandatory**: unconstrained `nondet_float()` admits `NaN`,
     and `NaN == NaN` is `False`, so the equivalence assertion would fail
     spuriously. (`assert nondet_float() == itself` → VERIFICATION FAILED.)
2. **The linear algebra is scalar-unrolled.** Matrix elements are kept in named
   scalar variables instead of Python lists, because ESBMC's Python *list* model
   cannot yet carry matrix elements through a matmul (see `bugs/`).
3. **`torch.allclose` is modelled explicitly** as the element-wise predicate
   `|a - c| <= atol + rtol*|c|` with torch's defaults (`rtol=1e-5`, `atol=1e-8`),
   using `math.fabs` and **inlined at each assertion** — it must not be factored
   into a Python helper function (see `bugs/bug2`, `bugs/bug3`).
4. **The proof obligation** is `assert allclose(A_elt, B_elt)` for every element
   of Q, K, V.

Because the fused matmul performs the *identical* multiply–add sequence per
output column as the unfused projection, the two are in fact **bit-exact** equal,
so the tolerance predicate holds trivially — and an exact `==` variant also
verifies (and is much faster for the solver).

## Files

| File | What it is | Expected verdict |
|---|---|---|
| `qkv_equiv.py` | The PoC: fused-vs-unfused QKV, `allclose` tolerance | `VERIFICATION SUCCESSFUL` |
| `qkv_equiv_fail.py` | Mutant: `split` takes K from the wrong (V) columns | `VERIFICATION FAILED` + counterexample |

## Running

```sh
esbmc qkv_equiv.py      --unwind 8     # SUCCESSFUL  (Bitwuzla default; FP tolerance is solver-heavy)
esbmc qkv_equiv_fail.py --unwind 8     # FAILED, with a concrete counterexample
```

Soundness notes:
- Use `--unwind` ≥ the largest loop bound **with unwinding assertions ON**.
  Pairing `--no-unwinding-assertions` with a short `--unwind` silently truncates
  loops and yields a *vacuous* SUCCESSFUL.
- An exact-equality variant (`assert A == B`) verifies in seconds and is the
  recommended smoke test; the tolerance variant is the faithful `allclose` model.

### Choosing the verification strategy

For **fixed dimensions** (as in `qkv_equiv.py`), every loop has a constant,
statically-known bound, so full unrolling is a *complete* proof — not a bounded
approximation:

- **`--unwind N` (N ≥ largest loop bound) with unwinding assertions on** — the
  recommended choice. The unwinding-assertion check is what certifies that no
  loop was truncated, so a SUCCESSFUL result is a real proof.
- **`--incremental-bmc`** — equally sound and more ergonomic: it raises the
  bound automatically until the unwinding assertions hold, so you don't have to
  compute the maximum loop bound by hand (it removes the "did I pick a big
  enough `--unwind`?" footgun). Slightly slower, same guarantee.
- **`--k-induction` / `--k-induction-parallel`** — *not* needed here. These
  prove properties of **unbounded** loops by induction; after fully unrolling
  constant-bound loops there is nothing to induct over, so they add machinery
  for no gain (and tend not to converge on nested matmul loops without supplied
  invariants).

To prove equivalence for **arbitrary dimensions** (symbolic `SEQ_LEN/D/H`, i.e.
a single size-independent result rather than one proof per size), the loops
become symbolically bounded and `--unwind` can no longer be complete. That is
exactly where **`--k-induction-parallel`** belongs — with the caveat that
matmul's nested loops generally need loop invariants to converge.

## ESBMC defects found while building this PoC

See `bugs/` — four reproducers, each independently confirmed on ESBMC 8.3.0:

1. `bug1_nestedlist_matmul.py` — nested-list matmul returns a **wrong value**
   (integer self-identity `R[0][0] == a*b` reports FAILED).
2. `bug1b_nestedlist_float_crash.py` — the float variant **crashes the SMT
   backend** (Bitwuzla `smt_sort.h:123`; Z3 `rm and fp sorts expected`).
3. `bug2_userfn_float_compare.py` — a user-defined **float-returning** function
   used in an FP comparison **crashes the backend** (`smt_ast.h:111` /
   `Projecting from non-tuple based AST`; Z3 `z3++.h:1855`).
4. `bug3_userfn_bool_compare.py` — a user-defined function that **returns a
   float comparison (bool)** produces a **wrong verdict** (FAILED where the
   inlined predicate verifies SUCCESSFUL). Likely the same root as #3.

These are why the PoC unrolls to scalars and inlines the `math.fabs` predicate.
Fixing #1 would let the natural, list/tensor-shaped code be verified directly; a
`torch` operational model (mapping `torch.mm/cat/split` onto the numpy OM, which
today lacks `concatenate`/`split`) is the larger follow-up.
