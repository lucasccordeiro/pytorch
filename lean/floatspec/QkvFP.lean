import FloatSpec.src.Core.Generic_fmt
open FloatSpec.Core.Generic_fmt

/-!
  QKV order-preserving fusion, proved over a *bit-precise* IEEE-754 rounding model
  using the **FloatSpec** library (a Flocq-style formalisation of IEEE-754 in Lean 4).

  This is the "re-run the experiment with a Lean FP library" companion to the
  core-Lean (`rfl` / `toBits`) version in `../QkvEquivalence.lean` and `../Bits.lean`.

  We model FP arithmetic as "apply rounding `r` after each operation", where `r`
  is any rounding to a representable format.  FloatSpec's `round_to_generic`
  (radix `beta`, format `fexp`, mode `mode`) is exactly such an `r` — covering
  every IEEE-754 precision and rounding mode.

  Build: needs FloatSpec + Mathlib (see README.md in this directory).
-/

-- FP dot product: round each multiply and each add, with rounding `r`.
def fdot (r : ℝ → ℝ) : List ℝ → List ℝ → ℝ
  | [],      _       => 0
  | _,       []      => 0
  | a :: as, b :: bs => r (r (a * b) + fdot r as bs)

def fproj (r : ℝ → ℝ) (x : List ℝ) (ws : List (List ℝ)) : List ℝ := ws.map (fdot r x)

/-- Order-preserving QKV fusion is exact under **any** rounding `r`, for **all**
    dimensions/head-counts — proved by `rfl`. -/
theorem qkv_fp_general (r : ℝ → ℝ) (x wq wk wv : List ℝ) :
    fproj r x [wq, wk, wv] = [fdot r x wq, fdot r x wk, fdot r x wv] := rfl

/-- The same, instantiated with FloatSpec's **IEEE-754 rounding** `round_to_generic`
    at an arbitrary radix/format/mode — a genuine bit-precise-FP equivalence. -/
theorem qkv_fp_ieee (beta : Int) (fexp : Int → Int) [Valid_exp beta fexp]
    (mode : ℝ → ℝ → Prop) (x wq wk wv : List ℝ) :
    fproj (round_to_generic beta fexp mode) x [wq, wk, wv]
      = [ fdot (round_to_generic beta fexp mode) x wq,
          fdot (round_to_generic beta fexp mode) x wk,
          fdot (round_to_generic beta fexp mode) x wv ] := rfl

-- FloatSpec really provides the IEEE-754 rounding used above:
#check (@round_to_generic)

/-
  Contrast with BMC. A *reassociating* fusion is NOT a definitional identity — it
  needs a concrete witness, e.g.
    round_to_generic … ((a+b)+c) ≠ round_to_generic … (a+(b+c)).
  FloatSpec's rounding is `noncomputable` (defined over ℝ), so Lean can neither
  *evaluate* it to a bit pattern nor *synthesise* a counterexample. That synthesis
  is exactly what a bounded model checker (ESBMC `--floatbv`) does automatically.
-/
