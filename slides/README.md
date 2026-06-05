# Slides

A non-expert-friendly status deck for the PoC.

- **`poc-status.html`** — self-contained slide deck. Open it in any browser
  (no build, no internet, no dependencies). Navigate with `←` / `→` / space;
  press `F` for fullscreen.
- **`poc-status.md`** — the same deck as [Marp](https://marp.app/) markdown
  (the editable source; also renders as plain markdown on GitHub).

## Editing

Edit `poc-status.md`, then keep `poc-status.html` in sync. To regenerate the
HTML (and a PDF/PPTX) from the markdown with Marp:

```bash
npx @marp-team/marp-cli@latest slides/poc-status.md -o slides/poc-status.html
npx @marp-team/marp-cli@latest slides/poc-status.md --pdf
```

The committed `poc-status.html` is hand-maintained so it works with zero tooling.
