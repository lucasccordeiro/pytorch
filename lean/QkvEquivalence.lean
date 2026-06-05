/-
  QKV fused-vs-unfused equivalence in Lean 4 (self-contained, no Mathlib).

  Companion experiment to the ESBMC PoC: the *same* property, discharged by an
  interactive theorem prover, to compare encoding/proof effort and fidelity
  (BMC vs ITP). The "agent" here is the LLM author writing the proof.

  Check it with:  lean QkvEquivalence.lean   (Lean 4; see lean-toolchain)
-/

-- Dot product over any dimension (a 1xD row times a Dx1 weight column).
def dot : List Int → List Int → Int
  | [],      _       => 0
  | _,       []      => 0
  | a :: as, b :: bs => a * b + dot as bs

-- "matmul" of one row x by a list of weight columns -> one output per column.
def proj (x : List Int) (ws : List (List Int)) : List Int := ws.map (dot x)

-- Unfused: three independent projections.
def unfused (x wq wk wv : List Int) : List Int := [dot x wq, dot x wk, dot x wv]

-- Fused: stack the weight columns, one projection, split (= identity on columns).
def fused (x wq wk wv : List Int) : List Int := proj x [wq, wk, wv]

/- (1) GENERAL theorem: holds for ALL inputs and ALL dimensions, by `rfl`.
   This is the size-general law that bounded model checking cannot give. -/
theorem qkv_general (x wq wk wv : List Int) :
    fused x wq wk wv = unfused x wq wk wv := rfl

/- (2) The same over Float.  The exact-order fusion preserves the operation
   order, so the identity is definitional and holds bit-for-bit in IEEE-754
   too (also `rfl`). -/
def dotF : List Float → List Float → Float
  | [],      _       => 0.0
  | _,       []      => 0.0
  | a :: as, b :: bs => a * b + dotF as bs

theorem qkv_general_float (x wq wk wv : List Float) :
    [wq, wk, wv].map (dotF x) = [dotF x wq, dotF x wk, dotF x wv] := rfl

/- (3) Where reals/integers and floating point DIVERGE.
   Integer addition is associative (provable by `omega`); a reassociating
   "optimisation" is sound over reals/integers. -/
theorem add_assoc_int (a b c : Int) : (a + b) + c = a + (b + c) := by omega

/- The Float analogue is FALSE in IEEE-754.  Lean cannot prove it and, unlike
   a model checker, returns NO counterexample -- only `rfl failed`:

     theorem add_assoc_float (a b c : Float) : (a + b) + c = a + (b + c) := by rfl
     -- error: Tactic `rfl` failed: ... not definitionally equal ...   (no witness)

   A concrete falsifying assignment exists (what ESBMC/BMC synthesises): -/
#eval ((0.1 + 0.2) + 0.3) == (0.1 + (0.2 + 0.3))   -- => false
