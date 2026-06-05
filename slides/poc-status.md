---
marp: true
title: Proving PyTorch optimizations correct with ESBMC
author: Lucas Cordeiro
description: A non-expert-friendly status update on the equivalence-verification PoC
theme: default
paginate: true
backgroundColor: #fbfbfd
color: #1d1d1f
style: |
  section { font-size: 26px; line-height: 1.45; }
  h1 { color: #0b5cad; }
  h2 { color: #0b5cad; }
  strong { color: #b3261e; }
  code { background: #eef2f7; }
  table { font-size: 22px; }
  section.lead { text-align: center; }
  section.lead h1 { font-size: 48px; }
  section.appendix { background: #f3f6fb; }
  footer { color: #8a8a8e; }
---

<!-- _class: lead -->

# Proving PyTorch optimizations are correct — automatically

### Formal equivalence checking of two PyTorch programs with ESBMC

**Lucas Cordeiro** · University of Manchester

A proof-of-concept · status update

---

## The problem, in one sentence

We constantly **rewrite** deep-learning code to make it run faster.

But how do we *know* the faster version computes the **same thing** as the original?

- A rewrite that is *almost* identical can silently change the results.
- Silently wrong math → wrong predictions, bugs that are very hard to find.

> We want a way to be **sure**, not hopeful — to **check an optimised version before it ships to production**.

---

## Our example: the "QKV" step inside every Transformer

Attention models — the **Transformer** design behind modern AI (e.g. ChatGPT) — build three things, **Q**, **K**, **V** *(intermediate matrices that decide what the model "pays attention" to)*, from the input `X` using three weight matrices.

**The clear way** (unfused) — three separate matrix multiplications:

```
Q = X · Wq      K = X · Wk      V = X · Wv
```

**The fast way** (fused) — glue the weights together, do **one** big multiply, then split:

```
W = [ Wq | Wk | Wv ]      QKV = X · W      → split into Q, K, V
```

These **should** give identical results. The question: do they — *always*?

---

## The two programs, side by side

```
  UNFUSED  (three matmuls)              FUSED  (one matmul + split)

         ┌── × Wq ──▶ Q                 X ─▶ W=[Wq|Wk|Wv] ─▶ X·W ─▶ QKV
   X ────┼── × Wk ──▶ K                                            │
         └── × Wv ──▶ V                                     split ─┼─▶ Q
                                                                   ├─▶ K
                                                                   └─▶ V

                    ≡   proven equal for every modelled input
```

ESBMC proves these two produce **the same result for every input we model**.

> So: a **faster implementation can be proven to behave exactly like the original**.

---

## How we check today: we test

We run the program on a **handful of example inputs** and compare.

🥄 *It's like tasting a few spoonfuls of soup and hoping the whole pot is fine.*

- Testing only covers the inputs you happened to try.
- A bug hiding in some other input is simply **missed**.
- **Passing tests ≠ correct.**

> **Testing gives confidence. Proof gives guarantees.**

---

## What we actually want: a proof, not a sample

Instead of trying a few inputs, check **every input we model — all at once** — mathematically.

*"Model" here = a defined tensor size and a bounded input range — not arbitrarily large programs.*

Two possible outcomes:

- ✅ **PROVEN equal** — guaranteed identical for *every* input in the model.
- ❌ **Counterexample** — one specific input where they differ, handed straight to you.

Either way, you learn something certain.

---

## The tool: ESBMC

**ESBMC** is an automated *model checker*.

1. It **reads the program** and turns the question
   *"are these two always equal?"* into one giant logic puzzle.
2. An automated **solver** *(a program that checks mathematical statements automatically)*
   then either finds an input that breaks it, or proves that **no such input exists** (within the model).

**Fully automated** once the program is encoded — you write **no** proofs by hand.

> The same kind of automated checking is **widely used in chip design and safety-critical software** (aerospace, automotive, medical).

---

## The trick that turns a test into a proof

| Ordinary test | Our verification |
| --- | --- |
| one **random** tensor `torch.randn(...)` | a **symbolic** tensor — one value standing for *all possible inputs at once* (bounded) |
| checks that one case | checks the **whole modelled range at once** |
| "looks fine" | a **guarantee — within the model** |

We assert `unfused result == fused result`, feed it *any* input in range, and let ESBMC settle it.

*(Inputs are bounded to a finite range to exclude oddities like "not-a-number". → Assumptions, backup.)*

---

## Result: the example is PROVEN correct

- ✅ Proven equal for **all inputs we model**.
- ✅ Proven **both senses of "equal"**: **bit-for-bit exact** (zero tolerance — literally identical, IEEE-754) **and** within **`torch.allclose`'s real tolerance** (`rtol=1e-5, atol=1e-8`).
- ✅ Proven in **two encodings**: plain-math (the matmul written out as explicit loops) **and** the *real* `torch.mm` + `torch.allclose`.
- ✅ When we **deliberately break it** (swap two columns), ESBMC **catches it** and shows the exact failing input.

> What "modelled" means (fixed sizes, bounded inputs) → **Assumptions & Scope**, backup slides.

---

## What the suite covers (and what it doesn't — yet)

**8 / 8 checks behave as expected.** That number is small *on purpose* — it is breadth, not scale:

| Dimension | Coverage |
| --- | --- |
| Problem classes | QKV projection · bias-fused linear (`X·W + b`) |
| Encodings | plain-math **and** torch-native (`torch.mm` / `torch.allclose`) |
| Strength of "equal" | **bit-for-bit exact** (zero tolerance) **and** **tolerance** (`torch.allclose` defaults) |
| Check type | a **proof** (clean ⇒ ✅) **and** a **refutation** (injected bug ⇒ ❌ + counterexample) |

So every case is double-checked: we prove the correct version *and* confirm a broken version is caught.

**This is an early-stage PoC** — small fixed sizes for now (see *Performance*, backup).

---

## Why this matters

- **All modelled inputs**, not a few → no hidden corner cases within the model.
- **Exact** → catches tiny numerical drift that testing would wave through.
- **Automated** → no hand-written proofs.
- **Actionable failures** → it hands you the precise input that breaks things.

> Concretely: **detect incorrect optimizations early** and **validate fusion / compiler transformations** *before* they ship — not after a model misbehaves in production.

---

## A bonus: we made the tool itself stronger

**In short: we taught ESBMC to understand PyTorch-style code** — 4 contributions merged upstream:

- A **`torch` operational model** — `mm`, `matmul`, `cat`, `split`, `allclose`.
- Fixes so **matrix math over nested lists works** — values/types survive function returns and copies.
- A **floating-point element-type fix** for matrices built by comprehension (we found, root-caused, and fixed it).

> Result: PyTorch-style code is now verifiable in ESBMC **at all** — reusable by anyone, not just us.

---

## Where we are · what's next

- ✅ Motivating **QKV** example **fully supported** (two encodings, exact proof).
- ✅ Extended to a **second** class: bias-fused linear (`X·W + b`).
- ⏭️ Today this runs on **small examples**; scaling to large, real-world models is **ongoing work** (see *Performance*, backup).

---

<!-- _class: lead -->

## Takeaway

**You can automatically check that a faster version of your code gives exactly the same result — before it ships and causes bugs.**

*Testing samples. This proves — and when it can't, it hands you the bug.*

<br>

For all inputs within a defined size and range · today on small examples · scaling is ongoing.

---

<!-- _class: appendix lead -->

# Backup slides

*Assumptions · Under the hood · Performance*

---

<!-- _class: appendix -->

## Assumptions & Scope

**What we prove**

- Equivalence of the two programs *as written*, for **all inputs in the modelled range**.
- Floating-point modelled **exactly** (IEEE-754, bit-precise) — not real arithmetic, not a hand-waved tolerance.

**What we model / bound**

- **Fixed tensor sizes** (bounded model checking; sizes are concrete, e.g. `S=1, D=2, H=1`).
- **Inputs bounded** to a finite range, which excludes `NaN`/`Inf`.

**What we do *not* claim**

- Arbitrary or symbolic sizes · performance equivalence · behaviour outside the bounds.
- We model a **sequential reference** semantics — not backend-specific optimisations (FMA, parallel reductions, cuBLAS).

---

<!-- _class: appendix -->

## Under the hood: how verification works

1. ESBMC **unrolls** the program (fixed sizes ⇒ finite) and turns each `assert` into a **verification condition**.
2. Tensors are modelled as lists of **IEEE-754 floats**; `torch.mm` / `torch.allclose` have operational models.
3. The condition is essentially: *for all bounded inputs,* `fused[i][j] == unfused[i][j]`.
4. An **SMT solver** (Bitwuzla / Z3) decides it. *(It searches for a breaking input: **none exists — UNSAT ⇒ proved**; **one found — SAT ⇒ that input is the counterexample**.)*

```python
X, Wq, Wk, Wv = symbolic, bounded         # any numbers in range
assert torch.allclose(unfused, fused)     # → one SMT formula over FP
```

---

<!-- _class: appendix -->

## Performance & current limits

Per-target runtime (default solver Bitwuzla, macOS arm64):

| Check | Time |
| --- | --- |
| scalar QKV proof | ~11 s |
| torch-native QKV proof | ~110 s |
| refuting a broken variant | 31 – 292 s |

- Cost grows quickly with tensor size (more multiply-adds → a bigger FP formula).
- `torch.cat` / `torch.split` are modelled but **unwinding-heavy** (a 1×1×3 `cat`+`split` ≈ 2.5 min) → we fuse/split by manual indexing for now.
- **Scaling to realistic sizes is the main open bottleneck** (tracked upstream).
