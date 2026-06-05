#!/usr/bin/env python3
"""Run the PyTorch / ESBMC equivalence-verification suite.

Each target is an entry script under ``harness/<name>.py`` that builds two
PyTorch programs (or two encodings of one program) over bounded
nondeterministic inputs and asserts their equivalence. ESBMC is invoked
directly on each entry script and its verdict is checked against the
expected one in the MANIFEST below.

Targets come in clean / ``_buggy`` pairs: the clean target must verify
(``VERIFICATION SUCCESSFUL``) and the mutant must be refuted
(``VERIFICATION FAILED``) -- so a vacuous "everything passes" regression
is caught by the mutant flipping to SUCCESSFUL.

The suite is single-phase (functional equivalence). The two-phase
scaffolding of the sister PoCs (AWS-Neuron, vLLM) is intentionally
omitted: phase-2 there is integer over/underflow + div-by-zero on host
index arithmetic, which does not apply to these floating-point
equivalence proofs. Integer-index targets added later can set
``safety_args`` / ``safety_expected`` to opt into a phase-2 run.

Usage:
  python3 verify.py                 # run every target
  python3 verify.py <name> ...      # run selected targets by manifest name
  ESBMC=/path/to/esbmc python3 verify.py    # point at a specific ESBMC build
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HARNESS = ROOT / "harness"
ESBMC = os.environ.get("ESBMC", "esbmc")

_USE_COLOR = sys.stdout.isatty()
_GREEN = "\033[32m" if _USE_COLOR else ""
_RED = "\033[31m" if _USE_COLOR else ""
_DIM = "\033[2m" if _USE_COLOR else ""
_RESET = "\033[0m" if _USE_COLOR else ""


@dataclass(frozen=True)
class Target:
    """One verification target: an ESBMC invocation and its expected verdict."""

    name: str
    entry: str                      # filename under harness/
    esbmc_args: tuple[str, ...]
    expected: str                   # "SUCCESSFUL" or "FAILED"


MANIFEST: list[Target] = [
    # Scalar-unrolled QKV equivalence (independent of the torch OM).
    # Proved both bit-for-bit exact (==) and within torch.allclose's tolerance.
    Target("qkv_equivalence_exact", "qkv_equivalence_exact.py",
           ("--unwind", "8"), "SUCCESSFUL"),
    Target("qkv_equivalence", "qkv_equivalence.py",
           ("--unwind", "8"), "SUCCESSFUL"),
    Target("qkv_equivalence_buggy", "qkv_equivalence_buggy.py",
           ("--unwind", "8"), "FAILED"),
    # Torch-native QKV equivalence (torch.mm + torch.allclose; esbmc#5120/#5131).
    # Exact = allclose(rtol=0, atol=0); tolerance = allclose defaults.
    Target("qkv_equivalence_torch_exact", "qkv_equivalence_torch_exact.py",
           ("--unwind", "4"), "SUCCESSFUL"),
    Target("qkv_equivalence_torch", "qkv_equivalence_torch.py",
           ("--unwind", "4"), "SUCCESSFUL"),
    Target("qkv_equivalence_torch_buggy", "qkv_equivalence_torch_buggy.py",
           ("--unwind", "4"), "FAILED"),
    # Bias-fused linear: X@W + b  vs  [X|1] @ [W;b]  (torch.mm + torch.allclose).
    Target("bias_linear", "bias_linear.py",
           ("--unwind", "4"), "SUCCESSFUL"),
    Target("bias_linear_buggy", "bias_linear_buggy.py",
           ("--unwind", "4"), "FAILED"),
]

_VERDICT_RE = re.compile(r"^VERIFICATION (SUCCESSFUL|FAILED)$", re.MULTILINE)


def run_target(t: Target) -> tuple[bool, str, float]:
    """Return (passed, observed_verdict, seconds)."""
    cmd = [ESBMC, str(HARNESS / t.entry), *t.esbmc_args]
    start = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    elapsed = time.monotonic() - start
    # ESBMC prints the verdict to stderr; search both streams to be safe.
    m = _VERDICT_RE.search(proc.stdout + "\n" + proc.stderr)
    observed = m.group(1) if m else "NO-VERDICT"
    return observed == t.expected, observed, elapsed


def main(argv: list[str]) -> int:
    selected = [a for a in argv if not a.startswith("-")]
    targets = MANIFEST
    if selected:
        by_name = {t.name: t for t in MANIFEST}
        missing = [n for n in selected if n not in by_name]
        if missing:
            print(f"unknown target(s): {', '.join(missing)}", file=sys.stderr)
            return 2
        targets = [by_name[n] for n in selected]

    width = max(len(t.name) for t in targets)
    failures = 0
    print(f"{_DIM}ESBMC = {ESBMC}{_RESET}")
    for t in targets:
        passed, observed, secs = run_target(t)
        if passed:
            tag = f"{_GREEN}PASS{_RESET}"
        else:
            tag = f"{_RED}FAIL{_RESET}"
            failures += 1
        print(f"  {tag}  {t.name.ljust(width)}  "
              f"expected={t.expected:<10} got={observed:<11} {secs:6.1f}s")

    total = len(targets)
    summary = f"{total - failures}/{total} passed"
    print(f"\n{_GREEN if failures == 0 else _RED}{summary}{_RESET}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
