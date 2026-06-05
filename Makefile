# ESBMC PyTorch equivalence-verification PoC.
#
# Point ESBMC at your build, e.g.:
#   make verify ESBMC=/path/to/esbmc/build/src/esbmc/esbmc
# or export ESBMC in the environment. Defaults to `esbmc` on PATH.
#
# Run a single target directly:
#   ESBMC=... python3 verify.py qkv_equivalence_torch

ESBMC ?= esbmc
export ESBMC

.PHONY: verify clean

verify:
	python3 verify.py

clean:
	rm -rf harness/__pycache__ __pycache__
