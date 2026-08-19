---
name: xuanzhi-design
description: Design and build web UI with a 宣纸 (xuan/rice paper) literati aesthetic — warm paper grounds, subtractive ink, one cinnabar accent, deckled sheets, seal chops, and hanging-scroll page structure. Use when a site should feel like ink on paper instead of pixels on glass, when asked for a Chinese paper-and-ink / ink-wash / 水墨 aesthetic, or when reviewing UI built in this language.
---

# 宣纸 Design — ink on paper, not pixels on glass

A design language for pages that behave like a mounted hanging scroll: paper is the ground, ink is the content, and everything decorative must earn its place the way a mark on a real scroll would. Every rule below was paid for in review rounds; the pitfalls are real failures, not hypotheticals.

Supporting references — read when you reach that part of the work:

- [paper.md](./paper.md) — building the 宣纸 sheet itself: deckled edges, grain, fades, and the CSS traps that make paper read as cardboard.
- [seals.md](./seals.md) — seal chops (印章): when one is allowed, how to cut one that isn't fake, where it goes.

## The palette method — 纸 / 墨 / 朱 / 青

Four roles, not four colors. Name your tokens by role:

| Role | Reference hex | Job |
| --- | --- | --- |
| paper 纸 | `#f3f2ea` (+ raised `#faf9f2`, deep `#eae8dc`) | the page field — warm, never white |
| ink 墨 | `#222a22` (+ soft `#3c453c`) | text, strokes, dark panels |
| cinnabar 朱 | `#c6472e` (+ deep `#a2371f`) | seals and accents — **the only hot color** |
| celadon 青 | `#a9bfad` (+ deep `#48604c`) | quiet secondary, rules, line art |

Rules that make it hold together:

- **One hot color.** Cinnabar is for seals, key accents, and nothing else. The moment a second saturated color appears, the page stops being paper.
- **Each role ships as a pair** (base + deep/soft) so small text and hairline strokes can step up contrast without introducing a new color. Hairline CJK serif strokes need the deep variant: a color that passes AA-large as a fill can be genuinely unreadable as thin serifs.
- **Saturated fills read as stickers on paper.** Where you want emphasis, use type size, hairline rules in the accent color, or ink panels — not colored blocks. A cinnabar rectangle on rice paper looks glued on.
- **Dark theme = role inversion, with one exception.** Paper and ink swap roles; ink pools become glowing frost on the night ground; the celadon pair swaps; cinnabar lifts. But any rule whose *meaning is directional* — "the page descends into dusk", "this recedes" — cannot be expressed in tokens that invert, or one theme will do the opposite of what the words say. Give directional surfaces their own non-swapping token pair and verify the description stays true in both themes.

## Ink behaves like ink

- **On paper, ink is subtractive.** Dark marks absorb light from the ground — build overlays and canvas effects by *darkening the paper*, never by drawing luminous strokes on top. Glow on a light ground is the single fastest way to break the metaphor. (On a dark theme the same content may glow — frost/aurora is the honest inversion.)
- **Brushwork is filled shapes, never stroked lines.** A brush stroke is a filled, tapered, variable-width polygon (press → belly → lifted flick). Constant-width round-cap strokes read as marker doodles, in SVG and canvas alike.
- **Additive color math: normalize by the peak channel, never clamp per channel.** `clamp(ground + c, 0, 1)` destroys hue exactly where the mark is densest (one channel saturates first and the color whites out at the core). Divide all channels by `max(peak, 1)` instead — identity when nothing clips, hue-preserving when something does. These bugs are density-dependent and invisible in static screenshots; test with heavy marks.

## Typography

- **Three latin voices:** a display face with real personality for headlines (normal width — never crushed-condensed), a workhorse body sans, and a mono for utility labels (lowercase, tracked wide). Reference stack: Bricolage Grotesque / IBM Plex Sans / IBM Plex Mono.
- **CJK is a serif, subset, and load-bearing.** Use a CJK serif (e.g. Noto Serif SC) subset to exactly the glyphs on the page (Google Fonts `text=` API); a full CJK font is megabytes for a handful of characters.
- **The gloss rule:** every CJK element must carry real meaning AND have an adjacent English reading (label, romanization, or caption). Decorative Chinese that means nothing is costume; Chinese without a gloss excludes most readers. One standing exception: a carved seal is a mark, not type — its reading goes in `aria-label`, never a visible caption (captioning a signature turns it into a diagram).
- **Restraint:** at most one mono eyebrow label per ~3 sections; one CTA per intent; no em-dashes as house style filler.

## Page structure — the hanging scroll (立轴)

When the aesthetic extends to whole-page structure:

- **The page is one object:** 天头 (head/header) → the painting/content → 题跋 (colophon — the contact/footer zone "where viewers add their own words") → 地头 (foot, closed by a roller bar). One continuous sheet of paper runs the full scroll — per-section paper panels read as a stack of cards, which is the thing this language exists to avoid.
- **Sections are stations**, each opened by a small vertical inscription in scroll vocabulary (作品 works · 笔法 method · 落款 signature · 题跋 colophon), glossed per the rule above.
- **Sheets vs plates.** Text sits on deckled paper sheets (soft, feathered — see [paper.md](./paper.md)). Artwork mounts as 画心 plates: the *only* boxed elements on the page (solid ink fill, ~3px radius, hairline celadon mounting rule, cast shadow). A scroll mounts its painting as a defined panel inside soft paper; everything else stays deckled. Never give a text sheet a card edge; never let artwork float unmounted.
- **The colophon ends darker than everything before it, in both themes** — see the directional-token rule above.

## Motion

- A stamp **presses down** (scale from ~1.28 with slight rotation); a grow-in reads as a popup badge.
- Type may **soak in** (blur → sharp) on load, like ink absorbing.
- Write-on reveals for brush strokes: animate a dash mask along the centerline of a *filled* shape, so the reveal is real brush travel.
- Wrap every animation in `@media (prefers-reduced-motion: no-preference)`; the reduced experience shows the completed state, not a frozen half-state.
- **Scrolling must never generate marks.** Velocity-driven effects fire every frame of a trackpad gesture and saturate the page; authored waypoint marks (one per station, on first arrival) are chosen — a flick is not.

## Review checklist

When reviewing UI in this language, check in order:

1. Is there exactly one hot color, spent only where it matters?
2. Does anything glow on the light theme? (Fail.)
3. Any text sheet with a visible card edge, or artwork without a mount? (Fail.)
4. Any CJK without meaning + gloss (seals excepted)?
5. Do directional statements ("deepens", "recedes") stay true in both themes?
6. Do fades land without a visible knee? (See [paper.md](./paper.md) — smoothstep, never two-stop linear.)
7. Reduced motion, no-JS, and both themes at real narrow widths?

## Anti-patterns (each rejected in real review)

- Flat hand-drawn SVG pictograms — tilted cards with glyphs, line-art hex grids, icon-style diagrams. They read as clip-art, not craft.
- CSS facsimile window chrome around code samples. Show the content on an ink panel instead.
- A brand glyph repeated as favicon + pins + status chips + watermark. A mark that appears everywhere is a logo, and a chop must not be a logo (see [seals.md](./seals.md)).
- Colored legend cells docked under a real control — anything button-shaped adjacent to a button reads as more controls.
- Theme names that are audience labels ("business", "pro"). Name themes after material and style (纸墨, 科技); keep audience words in URLs only.
- Baking text into raster artwork — a caption in an image is the one piece of type nobody can select, restyle, or translate.
