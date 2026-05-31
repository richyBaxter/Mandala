# Design system

Brand assets and the single source of design truth for **The Bitcoin Spiral / Mandala**.

> **Brand note:** the values here are the **houtini dark crypto-analytics** theme, used as a
> stand-in. To match **yubhub.co**, drop the real colours, fonts and logo in here and propagate
> (see "Rebranding" below).

## Files

| File | Purpose |
|---|---|
| `tokens.json` | Colours, fonts, radii, OG dimensions: the source of truth. |
| `logo.svg` | houtini wordmark + spiral mark (placeholder; replace with the real logo). |
| `make_og.py` | Generates `og-image.svg` (the social share card). Stdlib only. |
| `og-image.svg` | Generated share-card source → rendered to `/og.png` at repo root. |

## Where tokens are consumed

The same palette is duplicated in three places (kept in sync by hand for now):

1. **`generate.py`**: the `T = { … }` dict that styles the spiral SVG.
2. **`dashboard.html`**: the `:root { --… }` CSS variables.
3. **`design/make_og.py`**: reads `tokens.json` directly.

## Rebranding (e.g. to yubhub.co)

1. Edit `design/tokens.json` (colours + font).
2. Mirror the colours into `generate.py` (`T`) and `dashboard.html` (`:root`).
3. Replace `logo.svg` with the real logo; update the `HOUTINI` wordmark text in `make_og.py`,
   `generate.py` and the page headers if the brand name changes.
4. Regenerate artefacts:
   ```bash
   python3 generate.py
   python3 design/make_og.py
   python3 -c "import cairosvg; cairosvg.svg2png(url='design/og-image.svg', write_to='og.png', output_width=1200, output_height=630)"
   ```

## Future

A build step could read `tokens.json` and emit the CSS `:root` block and the `generate.py`
palette automatically, removing the manual duplication. Tracked in the root README roadmap.
