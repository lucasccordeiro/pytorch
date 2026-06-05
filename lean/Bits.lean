/-
  Bit-precise IEEE-754 facts in *core* Lean 4 — no library, no Mathlib.

  Lean's core `Float` is opaque (no `DecidableEq Float`), so a `Float` (dis)equality
  can't be discharged directly. But `Float.toBits : Float → UInt64` exposes the
  IEEE-754 bit pattern, and `UInt64` is decidable — so `native_decide` (which runs
  the compiled code) proves concrete bit-level FP facts.

  Check with:  lean Bits.lean
-/

-- The two associativity orderings of 0.1 + 0.2 + 0.3 have different bit patterns:
#eval (((0.1 : Float) + 0.2) + 0.3).toBits   -- 4603579539098121012
#eval ((0.1 : Float) + (0.2 + 0.3)).toBits   -- 4603579539098121011   (1 ULP apart)

/-- FP addition is **not** associative, proved bit-precisely in core Lean. -/
theorem fp_add_not_assoc :
    (((0.1 : Float) + 0.2) + 0.3).toBits ≠ ((0.1 : Float) + (0.2 + 0.3)).toBits := by
  native_decide

/-
  This proves a *concrete* bit-precise FP fact, but only for values you supply by
  hand: core Lean cannot *search* for the witness. Synthesising the counterexample
  from "∃ inputs where the rewrite differs" is what a bounded model checker
  (ESBMC `--floatbv`) does automatically.
-/
