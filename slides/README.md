# Slides

Two audiences, each in three interchangeable forms (HTML / Beamer PDF / Marp).

**Non-expert** (`poc-status.*`) — analogies, plain-language glosses, backup slides.

| File | Use |
| --- | --- |
| **`poc-status.html`** | Self-contained browser deck — no build/internet/deps. `←` / `→` / space, `F` for fullscreen. |
| **`poc-status-beamer.pdf`** | Ready-to-present PDF (from the Beamer source). |
| **`poc-status-beamer.tex`** | LaTeX **Beamer** source (TikZ QKV diagram). |
| **`poc-status.md`** | [Marp](https://marp.app/) markdown — editable source; also renders on GitHub. |

**Expert** (`poc-status-expert.*`) — assumes FV/embeddings/SMT background; adds the
formal-encoding detail, the verification pipeline, and an honest **BMC (ESBMC) vs
interactive proof (Lean) + LLM-agent** positioning.

| File | Use |
| --- | --- |
| **`poc-status-expert.html`** | Self-contained expert browser deck. |
| **`poc-status-expert-beamer.pdf`** / **`.tex`** | Expert Beamer PDF + source. |
| **`poc-status-expert.md`** | Expert Marp markdown. |

Both decks share the **side-by-side QKV diagram** (unfused three matmuls vs. fused
one-matmul-and-split). The non-expert deck is 18 slides; the expert deck is 14.

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
