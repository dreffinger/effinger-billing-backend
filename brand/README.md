# ehpa main logo and colour scheme (saved 2026-10-12, William: "save that artifact's design as the ehpa main logo and color scheme")

The design of the **ehpa Billing Button** page (https://claude.ai/artifact/5Eyw5K3ydS13uDHkR8JJyZ) is the ehpa brand.
Every ehpa page, app, installer and document uses this logo and these colours. This folder is the kit.

## The logo

A sky-blue ring that opens at the right and runs down, a magenta plus in the middle, on the deep hero square.

| File | Use |
|---|---|
| `ehpa-logo.svg` | the logo on its square, any size (web pages, documents) |
| `ehpa-mark.svg` | the ring and plus alone, transparent, for dark backgrounds and page headers |
| `ehpa-logo-256.png`, `ehpa-logo-1024.png` | raster copies (email, Slack, app stores) |
| `ehpa.ico` | Windows icon, 16 to 256 px; `desktop/icon.ico` is a copy |

Rules: the ring's opening stays at the right, running down (from 3 o'clock to about half past four). The mark is never
recoloured, rotated, outlined or squashed. On light backgrounds use the logo on its square, not the bare mark.

## The colours (Midnight, dark first)

| Token | Dark | Light | Used for |
|---|---|---|---|
| `--bg` | `#082f35` | `#ffffff` | page background |
| `--surface` | `#214449` | `#ffffff` | cards |
| `--surface-2` | `#2d5057` | `#f2f2f2` | inset fields, code chips |
| `--hero` | `#041d21` | `#082f35` | the logo square, hero panels |
| `--line` / `--line-strong` | `#1d4b53` / `#3c6169` | `#d7d8da` / `#bfbfbf` | borders |
| `--ink` / `--ink-2` | `#f4f5f7` / `#dee2e6` | `#082f35` / `#222428` | text |
| `--muted` / `--dim` | `#cacaca` / `#9da8b4` | `#636469` / `#737478` | secondary text, eyebrows |
| `--accent` | `#70d6f8` | `#0054e9` | links, primary buttons, the ring |
| `--accent-soft` | `#1f5a68` | `#e0f4fd` | soft highlights |
| `--magenta` | `#f841e0` | `#b5169b` | the plus, live mode, focus rings |
| `--ok` / `--ok-soft` | `#3dd475` / `#164a41` | `#1b8037` / `#dcfae6` | good |
| `--warn` / `--warn-soft` | `#ffc409` / `#3d4020` | `#917005` / `#fff3c4` | attention |
| `--bad` / `--bad-soft` | `#df7079` / `#3d1b22` | `#c5000f` / `#fbdcdf` | failed, danger |
| `--grad` | `135deg #70d6f8 → #f841e0` | `135deg #0054e9 → #b5169b` | the Run button |

Text is **Quicksand** (400 to 700); numbers and code are **JetBrains Mono** (500 to 600). Corner radii 8, 12 and 18 px, pills 999.
Dark is the default; light is used only when the device asks or the page's Theme button is pressed.

`ehpa-tokens.css` is the whole palette as a `:root` block to paste into a new page. `ehpa-brand.json` is the same for programs.

## Keeping it in step

`python3 brand/make_logo.py` rebuilds every file here from the page's own SVG and `:root` tokens, and refreshes the desktop
app's icon. Change the colours on the Billing Button page first, then run it; never edit the generated files by hand.
