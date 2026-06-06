# Validation: operational model vs. real PyTorch

The PoC's soundness is *modulo* the operational model (`torch.py`) faithfully
reflecting real PyTorch. `om_differential_test.py` turns that disclaimer into
**evidence**: it runs the OM's reference implementations (copied verbatim from
ESBMC's `src/python-frontend/models/torch.py`) against real `torch` on thousands
of random inputs, in **float64** (apples-to-apples IEEE-754; inputs in `[-10,10]`).

## Run

```bash
python3 -m venv venv && ./venv/bin/pip install torch
./venv/bin/python om_differential_test.py
```

## Result (PyTorch 2.12.0, float64, seed pinned)

```
mm        : 2000/2000 agree with torch.mm within IEEE-754 tolerance
            (of which 745/2000 bit-exact); max relative error 4.32e-13
cat/split : 2000/2000 bit-exact vs torch.cat/torch.split
allclose  : 4000/4000 same verdict as torch.allclose

PASS — OM is a faithful reference: cat/split/allclose exact; mm agrees up to rounding.
```

## What this establishes (and the honest caveat)

- **`cat` / `split` / `allclose` are bit-exact** with PyTorch — the data-movement
  ops and the closeness predicate the OM models match torch exactly.
- **`mm` agrees with `torch.mm` only up to IEEE-754 rounding** (max relative error
  ~4e-13), **not bit-for-bit**. `torch.mm` uses a different (blocked/BLAS)
  reduction order than the OM's sequential sum, so the last bits differ.

So the OM is a **faithful reference up to floating-point rounding**, which is the
right notion for a reference semantics. But it sharpens what the PoC proves:
the QKV equivalence is **bit-exact between the unfused and fused forms _within the
OM's sequential reduction order_** — it is *not* a claim that either matches a
specific deployed `torch.mm` binary bit-for-bit (different reduction order; and
backend FMA/parallel reductions are out of scope, as the deck states).
