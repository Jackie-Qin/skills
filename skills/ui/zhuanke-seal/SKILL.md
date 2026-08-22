---
name: zhuanke-seal
description: Cut a Chinese seal (印章/篆刻) from any short text — authentic public-domain 说文解字 小篆 glyphs or a user-supplied seal font, 朱文 or 白文, any color, output as color-agnostic SVG plus preview PNG. Use when asked to make a seal, chop, stamp, 印章, 闲章, name seal, or seal-style favicon/logo mark.
argument-hint: "[<text>]"
---

# 篆刻 — cut a seal

Generate a real-looking carved seal from text. The pipeline follows actual seal-carving practice: glyphs stretch to fill their cells (屈曲填满), stroke weight equalizes per glyph so every cell carries the same visual mass (疏密匀称), structured 残破 wear ages the cut the way a used stone actually wears (see below), and the silhouette is noise-eroded so it reads as stone, not vector.

Two scripts in `scripts/`:

- `fetch_glyph.py` — downloads `<char>-seal.svg` outlines from Wikimedia Commons, **verifying each is Public Domain** before saving, and records provenance in `SOURCES.md`.
- `cut_seal.py` — composes, carves, and traces the seal.

Dependencies: `python3` + Pillow, `magick` (ImageMagick), `potrace`, `rsvg-convert` (librsvg). All available via Homebrew/apt. Check with `--help` runs before promising results.

## 1. Ask the user

Unless already specified, ask (use AskUserQuestion where available; one round, don't interrogate):

| Choice | Options | Default |
| --- | --- | --- |
| **Text** | 1–8 characters. Traditional picks: a name (名章), a studio name (斋号), or a phrase with personal resonance (闲章) | — (required) |
| **Style** | 朱文 (red strokes on paper) / 白文 (red block, carved-away strokes) | 朱文 |
| **Glyph source** | Authentic 说文 小篆 from Commons (PD, verified) / a seal-script font file the user owns | Commons |
| **Color** | any hex; the SVG itself stays color-agnostic | cinnabar `#c6472e` |
| **Layout** | auto / single / column (1×N) / name (3 chars: full-height first + stacked pair) / grid (4 chars, 2×2) | auto |
| **Wear 残破** | none / light (25) / medium (50) / heavy (75), or any 0–100 | light |

Auto layout: 1 → single, 3 → name, 4 → grid, else column. Grid and column read **top to bottom, right column before left** — the scripts handle this; never reorder the text to "fix" it.

## 2. Fetch glyphs

```bash
python3 scripts/fetch_glyph.py --chars <text> --glyph-dir ./glyphs
```

If a character has no Commons seal outline, the script says so and fails closed. Offer the user: (a) reword the text, or (b) provide a seal-script font (`--font` path in the next step). Never substitute a lookalike character, and never generate a glyph with an image model — models back-port radicals from modern 楷书 forms and produce characters that do not exist (小篆 秦 is 廾 over 禾 and shares almost nothing with the modern shape).

## 3. Cut

```bash
python3 scripts/cut_seal.py --text <text> --glyph-dir ./glyphs \
  --style zhuwen --layout auto --color '#c6472e' --out ./out
```

Outputs `seal.svg` (`fill="currentColor"` — inherits any CSS color, mountable as `mask-image` per the xuanzhi-design skill's seals reference) and `seal-preview.png` (the seal in the chosen color on paper).

### Wear 残破

`--wear` ages the stone the way real seals wear: 破边 (composite crack-path bites through the border, with detached debris flecks), 残断 (jagged notches punched into strokes), 印泥不匀 (low-frequency blotchy thinning like uneven pressure), and a two-scale edge gnaw that pits every ink edge. It never adds ink and never smooths.

- **Deterministic:** without `--seed`, the wear derives from text+style+layout, so recutting the same seal reproduces it byte-for-byte. Pass `--seed <int>` to deal a different stone of the same age.
- **Small cuts take less.** At favicon/icon sizes chipping reads as noise, not age — use `--wear none` or `--wear light` for anything destined below ~64px.
- **Intensity guide:** light = a used stone that still prints crisply; medium = clearly old, edges crumbling; heavy = battered antique, legibility starts to suffer on multi-cell layouts.

## 4. Verify by looking — mandatory

Open/view `seal-preview.png` before delivering. Check:

1. **Every glyph is the right character.** Compare against its Commons page (linked in `glyphs/SOURCES.md`). A wrong character on a seal is not a style defect — it's gibberish carved in stone.
2. **Reading order**: top→bottom, right column first.
3. **Even ink density** across cells — no starved or bloated character.
4. **Legibility at target size.** A multi-cell seal that looks great at 256px averages into a smudge at 16px. For favicon-size use, cut a **separate single-character seal** with much heavier weight and border (`--layout single`, and expect to raise the ink targets) — that's what a carver would do for a smaller stone, rather than scaling the big one down.
5. **Wear reads as age, not damage.** Bites should be uneven and clustered — if wear looks uniform or mechanical, drop the level; if no break is visible at display size, raise it. Confirm legibility survives the worn cut at the size it will actually render.

## 5. Deliver

Give the user both files, state the license facts (glyph outlines are Public Domain, provenance in `SOURCES.md`; the composition is theirs), and — if the seal is going on a web page — point to the mounting and restraint rules in the xuanzhi-design skill: at most two seals per page, a chop marks the scroll but is never a logo, and readings go in `aria-label`, not a visible caption.
