# Lean comparison: ITP vs. the ESBMC (BMC) PoC

A like-for-like experiment: prove the **same QKV fused-vs-unfused equivalence** in
the Lean 4 interactive theorem prover, to put real numbers behind the
"BMC vs ITP" slide. The "agent" is the LLM author writing the proof.

## Run

```bash
elan default stable          # or: leanprover/lean4:v4.30.0 (see lean-toolchain)
lean QkvEquivalence.lean     # checks in a few seconds; no Mathlib required
```

## What we measured

| | **Lean (ITP)** | **ESBMC (BMC)** |
| --- | --- | --- |
| Setup | Lean 4.30, **no Mathlib** | ESBMC + torch operational model |
| Encoding | ~30 LOC (`dot`/`proj`/`fused`/`unfused`) | ~40-line Python harness |
| QKV fusion proof | **`rfl`, first attempt** | per-shape SMT |
| Generality | **∀ dimensions & head-counts** (one theorem) | bounded: fixed shapes only |
| Over `Float` | also `rfl` (order preserved ⇒ bit-for-bit) | bit-precise IEEE-754, ~110 s |
| Check time | ~5 s (mostly startup) | 6–135 s per target |

## The decisive finding

The QKV fusion is **order-preserving** — the fused column is the *identical*
multiply–add sequence as the unfused projection. So the equivalence is a
**definitional identity**: Lean closes it with `rfl`, generalised to all
dimensions, and it holds over `Int`, `ℝ`, and `Float` alike.

The tools diverge on **reassociating** optimisations:

- Over `Int`/`ℝ`, addition is associative — `add_assoc_int` is proved by `omega`.
- Over `Float` it is **false**. Lean cannot prove `(a+b)+c = a+(b+c)` for
  `Float` and returns **no counterexample** — only `rfl failed`. A witness
  exists (`(0.1+0.2)+0.3 ≠ 0.1+(0.2+0.3)`, see the `#eval`), which a bounded
  model checker like ESBMC synthesises automatically.

## Takeaway

- **ITP wins generality**: ∀-shape theorems, trivially, for order-preserving fusions.
- **BMC wins bit-precise FP + counterexamples**: exactly the reassociating fusions
  that are the *actually risky* ones, where the algebraic (`ring`/`omega`) leverage
  Lean relies on is unsound for IEEE-754.

They are complementary, which is the point of the deck's "when to use which" slide.
