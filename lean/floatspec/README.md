# Re-run with a real Lean IEEE-754 library (FloatSpec)

This is the "re-run the experiment using a Lean FP library" companion to the
core-Lean version (`../QkvEquivalence.lean`, `../Bits.lean`). It proves the QKV
order-preserving fusion over **FloatSpec**'s bit-precise IEEE-754 rounding —
confirming that Lean *does* support IEEE-754 (via a library), and characterising
what that buys vs. ESBMC.

[FloatSpec](https://reservoir.lean-lang.org/@Beneficial-AI-Foundation/FloatSpec)
is a Flocq-style formalisation of IEEE-754 in Lean 4 + Mathlib.

## Setup (needs Mathlib — heavy)

```bash
mkdir fpdemo && cd fpdemo
cat > lakefile.toml <<'TOML'
name = "fpdemo"
[[require]]
name = "FloatSpec"
git = "https://github.com/Beneficial-AI-Foundation/FloatSpec"
[[lean_lib]]
name = "fpdemo"
TOML

lake update                                   # resolves FloatSpec + Mathlib
cp .lake/packages/mathlib/lean-toolchain .    # align toolchain to Mathlib's (v4.29.0)
lake exe cache get                            # download Mathlib oleans (~GB, 8232 files)
lake build FloatSpec                          # build the library (cached ⇒ minutes)

cp /path/to/QkvFP.lean .
lake env lean QkvFP.lean                      # checks in ~20 s
```

## Result

`QkvFP.lean` checks (`exit 0`): both `qkv_fp_general` (any rounding `r : ℝ → ℝ`)
and `qkv_fp_ieee` (FloatSpec's `round_to_generic`, any radix/format/mode) are
proved by `rfl`, for **all dimensions** — a genuine bit-precise IEEE-754
equivalence, not just a core-`Float` definitional trick.

## Findings

- **Lean *does* do bit-precise IEEE-754** — proved the QKV equivalence over
  FloatSpec's actual IEEE-754 rounding (∀ dims, any precision/mode). The earlier
  "Lean has no bit-precise FP" framing was wrong.
- **But FloatSpec is a proof model, not an executor.** It is Flocq-style and
  **`noncomputable`** (`round_to_generic` / `B754_to_R` are defined over ℝ). So
  Lean cannot *evaluate* it to a bit pattern or *synthesise* a counterexample — a
  reassociating fusion would need a concrete witness FloatSpec won't produce.
  (Core Lean *can* check a hand-supplied bit fact via `toBits` + `native_decide`;
  see `../Bits.lean`. It still can't *search* for one.)
- **Cost.** One-time setup is dominated by the Mathlib cache (~GB, 8232 oleans)
  and the FloatSpec build (3344 jobs, minutes from cache); checking the proof is
  then ~20 s. ESBMC's torch-native proof is ~110 s with **zero** library setup
  and runs on the real Python.

## Takeaway (sharper than before)

Lean + an FP library is the right tool for **general, machine-checked FP
*theorems*** (∀ shapes; error bounds; rounding lemmas — FloatSpec ships Sterbenz,
relative-error, double-rounding, …). ESBMC is the right tool for **checking real
optimised code bit-precisely and *finding* the counterexample** when a rewrite is
wrong. The two are complementary; for *this* PoC's goal (validate optimised
PyTorch), ESBMC remains the better fit — now for the right reasons.
