# Seal chops (印章)

The cinnabar seal is the most tempting element in this language and the easiest to ruin. The failure mode is not ugliness — it's turning a chop into a logo, or shipping a character that doesn't exist.

## A chop is not a logo

The one rule everything else follows: **a chop may mark the scroll; it may not be a brand mark.** A glyph repeated as favicon + map pins + status chips + watermark is a logo wearing seal costume, and the whole system reads as branding. If you find the same seal in more than two places, delete it everywhere and start over.

The traditional roles justify at most two seals per page, and neither repeats:

| Seal | Traditional role | Placement |
| --- | --- | --- |
| 引首章 (leading seal) | opens a scroll | head of the page, off to one side — it also reclaims dead space at the top |
| 名章 (name seal) | signs the work | the colophon/contact zone, where a painting is actually signed |

A 闲章 (leisure seal) traditionally carries a phrase with a personal resonance — an allusion, a motto, a riff on the owner's name — not the owner's brand. Do not add a third chop without a reason a real scroll would recognize.

## Seals are not glossed

The site-wide CJK gloss rule governs CJK *type*. A carved chop is a mark on the paper, and captioning it turns a signature into a diagram. The reading lives in `aria-label`, so the page still states what each seal says to anyone who cannot see it. This is the one standing exception — do not "fix" it by adding a visible caption.

## Cutting a seal that isn't fake

**Glyphs come from public-domain 小篆 (seal script) reference outlines — 说文解字-derived sources on Wikimedia Commons — never from a generator and never adapted from the modern form.** This is load-bearing: image models back-port radicals from the modern 楷书 glyph into "seal script", producing characters that do not exist. The result reads as plausible seal script to anyone not checking stroke-by-stroke — and a wrong character on a name chop is not a style defect, it's a forgery of nothing. Verify every glyph against its reference before cutting it, and record the provenance of each outline you vendor.

Composition principles from real seal carving:

- **屈曲填满** — glyphs legitimately distort to fill their cells. Trim each outline to its ink, then stretch-fit into the cell.
- **疏密匀称** — even ink density across cells. Thicken strokes **per glyph** to a target density: sparse characters (few strokes) need fatter strokes, or one uniform dilation starves them and the seal looks patchy.
- Draw 界格 (cell rules) and a border; then roughen — noise-threshold the silhouette so the edge reads as carved stone, not vector.
- 朱文 (red characters on paper ground) is the default register for this language; the seal is cinnabar ink, not a filled red block.

## Mounting

Mount the seal as CSS `mask-image` over `background-color`, not as an `<img>` and not as inline SVG with a baked fill:

- the chop inherits the theme's cinnabar token instead of hard-coding a hex,
- it satisfies a strict `style-src 'self'` CSP (no inline fills),
- it's one cached asset instead of kilobytes of path data per page.

Position per the sheet rules: **a chop clears the feather, not the geometric edge** — derive its insets from the sheet's fade tokens so a visible margin of solid paper surrounds it at every viewport. A chop stamped on the fade looks stamped on fog.

If animated, a stamp **presses down** (scale from ~1.28, slight rotation, settling onto the paper). A grow-in or fade-in reads as a popup badge.
