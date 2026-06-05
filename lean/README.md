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
- Over Lean's **core `Float`** it is **false**, and core `Float` is *opaque*
  (no semantics in the logic), so Lean cannot prove `(a+b)+c = a+(b+c)` — only
  `rfl failed` — and returns **no counterexample**. A witness exists
  (`(0.1+0.2)+0.3 ≠ 0.1+(0.2+0.3)`, see the `#eval`), which a bounded model
  checker like ESBMC synthesises automatically.

> **Lean *does* support IEEE-754 — via libraries, not core.** Dedicated
> formalisations give bit-precise FP in Lean: **FloatSpec** (general IEEE-754),
> **TorchLean** (IEEE-754 binary32 for neural-network verification), **FLoPS**
> (the P3109 low-precision standard). With one of these you *can* reason about FP
> rounding in Lean — at the cost of building/adopting the model and writing the
> proofs, and still without a model checker's automatic counterexamples. The
> contrast below is therefore **automation + counterexamples + checking the real
> code**, not "Lean can't do FP".
>
> We actually re-ran the experiment this way: **`floatspec/`** proves the QKV
> fusion over FloatSpec's real IEEE-754 rounding (`round_to_generic`, ∀ dims, by
> `rfl`), and **`Bits.lean`** proves a concrete bit fact in *core* Lean via
> `toBits` + `native_decide`. See [`floatspec/README.md`](./floatspec/README.md).

## Takeaway

- **ITP wins generality**: ∀-shape theorems, trivially, for order-preserving fusions.
- **BMC wins bit-precise FP + counterexamples**: exactly the reassociating fusions
  that are the *actually risky* ones, where the algebraic (`ring`/`omega`) leverage
  Lean relies on is unsound for IEEE-754.

They are complementary, which is the point of the deck's "when to use which" slide.

## Can ESBMC reach Lean-class proof times? (encoding experiment)

Lean checks the (real-arithmetic) theorem in ~5 s. ESBMC's default is *bit-precise*
IEEE-754 (`--floatbv` on Bitwuzla). We measured the alternative encodings
(`--ir` = integer/real arithmetic; `--ir-ieee` = real arithmetic with IEEE
enclosure constraints; both need an int/real solver, i.e. `--z3`):

| Target | `--floatbv` (Bitwuzla, default) | `--ir --z3` | `--ir-ieee --z3` | `--floatbv --z3` |
| --- | --- | --- | --- | --- |
| scalar exact (proof) | 6.1 s | **2.9 s** | **2.9 s** | ≫12 min (killed) |
| scalar tolerance (proof) | 13.1 s | **5.5 s** | — | — |
| scalar buggy (refutation) | ~300 s | ≫19 min (killed) | — | — |
| torch-native exact (proof) | ~122 s | ≫5 min (killed) | ≫5 min (killed) | — |

**Yes — but only for the easy case, and only by becoming Lean.** `--ir`/`--ir-ieee`
reach ~3 s on the scalar proof (≈ Lean), but they *abstract* floating point
(`--ir` to reals, `--ir-ieee` to a real enclosure), so that is the
Lean-equivalent (real-arithmetic) claim, **not** the bit-precise one. And the
same encodings **diverge** on the cases that motivate BMC — refutation
(counterexample search) and the operational-model torch path. The solver pairing
also dominates: Z3 + `--floatbv` is ≫100× slower than Bitwuzla + `--floatbv`.

**Conclusion:** bit-precise `--floatbv` on Bitwuzla (the default) is the robust
choice across proofs, refutations, and the torch OM; the int/real encodings buy
Lean-class speed only by giving up exactly what BMC is here for.

## Lean vs. ESBMC `--ir` (apples-to-apples: both real arithmetic)

With `--ir`, ESBMC reasons over **reals** — the same semantic level as the Lean
proof (no bit-precise FP). At that level the two are directly comparable:

| Aspect | **Lean (ITP)** | **ESBMC `--ir` (BMC)** |
| --- | --- | --- |
| Arithmetic | exact reals / integers (no FP) | integers + reals (FP abstracted) |
| Order-preserving QKV proof | `rfl`, ~5 s | UNSAT, ~3 s (scalar) |
| Generality | **∀ dimensions** (one theorem) | **bounded** — fixed shapes only |
| What is checked | machine-checked proof (small kernel TCB) | UNSAT over the bounded domain (solver + frontend TCB) |
| Effort | encode types, state theorem, write proof | write the program (= spec), push-button |
| Counterexamples | none (failed proof ≠ witness) | concrete for real-distinguishable cases — but nonlinear-real SAT can diverge (buggy `--ir` killed >19 min) |
| Reassociation | sound (`ring`/`omega`), **false in FP** | also "holds" (reals), **FP-blind** |

**Upshot:** `--ir` makes the two genuinely close — same real-number semantics,
similar few-second times on the order-preserving proof. The residual differences:
Lean is **unbounded / ∀-shapes** and kernel-checked; ESBMC `--ir` is **bounded**
but **push-button** (program = spec). And **neither captures bit-precise IEEE-754
in this mode**, so neither catches FP-reassociation bugs — that needs ESBMC's
default `--floatbv` (which also yields the counterexample).

> Minor tooling note: `--ir-ieee` without `--z3` aborts on the default Bitwuzla
> ("Bitwuzla does not support integer encoding mode") instead of auto-selecting a
> compatible solver or erroring cleanly — worth an upstream UX fix.

