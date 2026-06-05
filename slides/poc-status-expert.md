---
marp: true
title: Formal equivalence checking of PyTorch programs with ESBMC (expert)
author: Lucas Cordeiro
description: Expert-audience version — encoding effort and BMC-vs-ITP positioning
theme: default
paginate: true
backgroundColor: #fbfbfd
color: #1d1d1f
style: |
  section { font-size: 25px; line-height: 1.4; }
  h1 { color: #0b5cad; }
  h2 { color: #0b5cad; }
  strong { color: #b3261e; }
  code { background: #eef2f7; }
  table { font-size: 20px; }
  section.lead { text-align: center; }
  section.lead h1 { font-size: 44px; }
  footer { color: #8a8a8e; }
---

<!-- _class: lead -->

# Formal equivalence checking of PyTorch programs with ESBMC

### Bounded model checking for fusion/rewrite correctness — and how the encoding compares to interactive proof

**Lucas Cordeiro** · University of Manchester

Proof-of-concept · status update *(expert version)*

---

## Problem & threat model

Optimising transformations — **operator fusion, kernel rewrites, compiler passes** —
must be *semantics-preserving*. We want to decide:

$$\forall\, X, W \text{ with entries in } [-10,10].\quad P_{\text{unfused}}(X,W) \equiv P_{\text{fused}}(X,W)$$

- **Testing** under-approximates: it samples a finite input set.
- We want **exhaustive** equivalence over an input region, with **bit-precise IEEE-754**
  semantics (where fusion actually breaks: reassociation, rounding).
- Two verdicts: **proof** (UNSAT) or a **concrete counterexample** (SAT).

*Checked under a **sequential IEEE-754 semantics**; inputs are bounded, so **NaN/Inf are excluded** — equivalence is proven over finite FP domains. **Not modelled:** backend optimisations (FMA, cuBLAS), parallel/tree reductions, non-deterministic scheduling.*

---

## Running example: QKV projection

$$
\text{unfused: } Q = XW_q,\; K = XW_k,\; V = XW_v
\qquad
\text{fused: } W = [W_q\,|\,W_k\,|\,W_v],\; \mathit{QKV}=XW,\; \text{split}
$$

The fused column $j$ is the **identical multiply–add sequence** as the corresponding
unfused projection ⇒ the two are equal **bit-for-bit under the same evaluation order**
(sequential IEEE-754), not merely within a tolerance. Both claims are checked (below).

---

## The two programs, side by side

```
  UNFUSED  (three matmuls)              FUSED  (one matmul + split)

         ┌── × Wq ──▶ Q                 X ─▶ W=[Wq|Wk|Wv] ─▶ X·W ─▶ QKV
   X ────┼── × Wk ──▶ K                                            │
         └── × Wv ──▶ V                                     split ─┼─▶ Q
                                                                   ├─▶ K
                                                                   └─▶ V

                    ≡   bit-for-bit equal for every input in the modelled region
```

---

## The embedding (1/2): encoding design

The program **acts as the specification** under the assumed operational model
(correctness depends on the OM's faithfulness) — no separate spec to maintain.

- **Tensors** → nested Python lists; **ops** → an operational model `torch.py`
  (`mm`, `matmul`, `cat`, `split`, `allclose`) — pure-Python, float-typed reference
  semantics, compiled into the ESBMC binary.
- **Inputs** → symbolic `nondet_float()` with `__ESBMC_assume` range bounds
  (excludes NaN/Inf ⇒ finite FP domain).
- **Shapes** → dimensions are **fixed and well-typed**; shape compatibility is assumed.
- **Property** → an assertion: exact (`==` / `allclose(rtol=0, atol=0)`) or
  tolerance (`allclose` defaults `1e-5/1e-8`).
- **Two encodings**: scalar-unrolled (no OM) **and** torch-native (through the OM).

---

## The embedding (2/2): example harness

```python
X   = [[bounded() for _ in range(D)] for _ in range(S)]   # symbolic, bounded
QKV = torch.mm(X, torch.cat([Wq, Wk, Wv], dim=1))        # fused weight (cat, dim=1)
assert torch.allclose(torch.mm(X, Wq), split_Q(QKV), 0.0, 0.0)   # exact
```

Symbolic bounded inputs; the matmul goes through the operational model; the property
asserts exact (zero-tolerance) equivalence of the unfused and fused *Q*. *(In the PoC,
`cat`/`split` are realised by manual column indexing — `torch.cat`/`split` are unwinding-heavy.)*

---

## Pipeline & soundness

Python frontend → **GOTO** → symbolic execution → **VCs** → SMT.

- Fixed dims ⇒ loops fully unwound; **unwinding assertions ON** (no vacuous SUCCESS on
  truncation). Symbolic dims ⇒ `--k-induction` with convergence.
- **Bit-precise IEEE-754** in the FP theory (Bitwuzla / Z3); rounding is modelled, not abstracted.
- **UNSAT ⇒ proved** over the region; **SAT ⇒ the falsifying assignment** is reported.
- TCB: the Python frontend + operational model + SMT solver.
- **Not modelled**: backend-specific optimisations (FMA, parallel/tree reductions, cuBLAS). **Intended use: reference-semantics equivalence**, not production-kernel equivalence.

---

## Results

**8 / 8** — QKV proved *exact* and *tolerance*, in *scalar* and *torch-native* encodings;
each clean target paired with a refuted mutant. Bitwuzla, fixed dims (S=1,D=2,H=1 torch; 2×2 scalar).

| Target | predicate | verdict | time |
| --- | --- | --- | --- |
| `qkv_equivalence_exact` | scalar `==` | SUCCESSFUL | 6 s |
| `qkv_equivalence` | scalar tolerance | SUCCESSFUL | 12 s |
| `qkv_equivalence_torch_exact` | `allclose(0,0)` | SUCCESSFUL | 122 s |
| `qkv_equivalence_torch` | `allclose` defaults | SUCCESSFUL | 124 s |
| `*_buggy` (×3, swap/zero) | refutation | VIOLATED (c.ex.) | 35–338 s |
| `bias_linear` (+`_buggy`) | `X·W+b` ≡ `[X\|1]·[W;b]` | SUCCESSFUL / VIOLATED | 35–135 s |

**Legend:** ✓ SUCCESSFUL = property holds (UNSAT); ✗ VIOLATED = counterexample found (SAT). The `*_buggy` targets are intentional mutants, so a counterexample is the **desired** outcome (non-vacuity check).

---

## The embedding was *not* free

Driving real PyTorch-style code through ESBMC required fixing the embedding path —
**4 contributions merged upstream**:

- **`torch` operational model** ([#5120](https://github.com/esbmc/esbmc/pull/5120)).
- **Nested-list value/type across returns & copies** ([#5111](https://github.com/esbmc/esbmc/pull/5111), [#5113](https://github.com/esbmc/esbmc/pull/5113)) — fixes #5102/#5103.
- **Homogeneous nested-list FP element-type** ([#5131](https://github.com/esbmc/esbmc/pull/5131), fixes #5129) — found, root-caused, fixed by this PoC.

> i.e. the *embedding cost* here was partly tool-engineering, now amortised for everyone.

---

## ESBMC (BMC) vs Lean (ITP) + LLM agent

| Aspect | **ESBMC (BMC)** | **Lean (ITP) + LLM agent** |
| --- | --- | --- |
| Embedding effort | program acts as spec under the OM (write both, assert `≡`) | embed tensor + FP semantics, **state** the theorem |
| Automation | push-button: auto VC-gen + SMT | interactive; an agent can drive tactic search, but proofs need guidance |
| FP semantics | **bit-precise IEEE-754** native | must be modelled/axiomatised; bit-level reasoning is heavy |
| Counterexamples | **concrete falsifying input** (SAT) | none by default (failed proof ≠ witness) |
| Scope | **bounded** — fixed sizes, finite unwinding | **unbounded / size-general**, kernel-checked |
| TCB | frontend + OM + solver | small proof kernel |

---

## When to use which

- **Gate rewrites with BMC (ESBMC):** automatic, bit-precise, bug-finding, on concrete shapes
  — fast feedback in CI, and a *counterexample* when it breaks.
- **Reach for ITP (Lean) for the size-general law:** when you need $\forall$ shapes, machine-checked.
- They **compose**: BMC to find bugs and certify the configurations you ship; ITP for the
  general theorem (where the **encoding + proof effort** — and the lack of FP counterexamples —
  is the real cost the reviewer is asking about).

> For "is this fusion correct for the shapes we deploy?", push-button BMC with bit-precise FP
> and counterexamples is highly effective in practice.

---

## Status · what's next

- ✅ QKV fully verified (exact + tolerance, 2 encodings); bias-fused linear added.
- ⏭️ **Scale**: larger/symbolic dims via k-induction; native `cat`/`split`
  (currently unwinding-heavy — [#5121](https://github.com/esbmc/esbmc/issues/5121)).
- ⏭️ A like-for-like **Lean + agent** encoding of the same equivalence, to quantify the
  encoding/proof effort empirically.

*Scalability is bounded by **SMT solving over floating-point arithmetic** and **loop unwinding** — cost grows rapidly with tensor size and FP-operation count.*

---

<!-- _class: lead -->

## Summary

Bounded model checking gives an **automatic, bit-precise, counterexample-producing**
equivalence check for PyTorch rewrites — at the cost of being **bounded**.

The encoding cost is **relatively low once the operational model is available** (the program
acts as the spec); interactive proof buys generality at a higher encoding/proof cost and
**no counterexamples**.

<br>

*All results are reproducible via the ESBMC harnesses and the `torch` operational model (`make verify`).*
