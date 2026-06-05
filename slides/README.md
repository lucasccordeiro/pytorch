# Slides

A non-expert-friendly status deck for the PoC, in three interchangeable forms.

| File | Use |
| --- | --- |
| **`poc-status.html`** | Self-contained browser deck — no build, no internet, no deps. `←` / `→` / space to navigate, `F` for fullscreen. |
| **`poc-status-beamer.pdf`** | Ready-to-present PDF (compiled from the Beamer source). |
| **`poc-status-beamer.tex`** | LaTeX **Beamer** source (TikZ QKV diagram). |
| **`poc-status.md`** | [Marp](https://marp.app/) markdown — editable source; also renders as plain markdown on GitHub. |

All three carry the same 13-slide story, including a **side-by-side QKV diagram**
(unfused three matmuls vs. fused one-matmul-and-split, with a "proven equal" badge).

## Regenerating

Beamer → PDF (run twice for the page refs):

```bash
cd slides
pdflatex poc-status-beamer.tex
pdflatex poc-status-beamer.tex
```

Marp → HTML / PDF / PPTX:

```bash
npx @marp-team/marp-cli@latest slides/poc-status.md -o slides/poc-status.html
npx @marp-team/marp-cli@latest slides/poc-status.md --pdf
```

The committed `poc-status.html` is hand-maintained so it works with zero tooling.
