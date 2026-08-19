# Building the 宣纸 sheet

The sheet is the hardest artifact in this language to get right: it has to read as a physical piece of paper laid on the page, and nearly every obvious CSS construction makes it read as a rectangle, a cloud, or nothing at all. These are the mechanics that survived review.

## Construction: blurred solid, never radial gradient

Build every soft paper/pool shape ONE way: a pseudo-element with a **solid fill**, an irregular `border-radius`, and `filter: blur()`, inset negative so it bleeds past its box (parent needs `overflow: clip`).

Never build these from radial gradients. Two failure modes, both certain:

1. An ellipse whose radius exceeds its own box is **cut off square** — a visible card edge exactly where you wanted a feather.
2. A multi-ellipse pool **fades toward its corners**, washing out label ends and short lines. A blurred solid keeps a fully opaque core under the type and cannot clip.

## A sheet is a rectangle with deckled corners, never an ellipse

- Use **absolute corner radii, not ~50%**. Percentage radii inscribe an ellipse that cannot reach its own corners — content near a corner falls off the paper.
- The blur does the feathering; the shape stays rectangular. Amorphous ~50%-radius blobs read as accidental erasures in the wash, not paper.
- Scale the blur with the sheet: a blur that feathers a small panel still reads as a hard rectangle at full-section scale. Expect roughly 1.5× the blur when a sheet grows from panel to section size.

## One whole piece of paper

For a long page, the sheet lives on the top-level content container and runs unbroken from head to foot — a scroll is one piece of paper. Consequences:

- **The sheet is deliberately not opaque** (≈0.9). Fully opaque paper over a full-page background deletes the background from the page; at ~0.9 the ground soaks *through* the paper the way ink actually behaves. This couples the sheet opacity to how dark the background may ever get: **the background's darkness floor and the sheet's opacity are one design** — recompute text contrast over the worst-case ground before changing either, and never change one without the other.
- **Feather the sides only, with linear gradients.** A full-page sheet is thousands of pixels tall; `filter: blur()` on it rasterizes one enormous layer. The side edges are the only ones ever seen (head and foot sit under header/footer surfaces), so feather them with linear-gradient masks. Linear gradients cannot clip the way an ellipse can, so the no-gradient rule does not apply to them.

## The sheet must be visible

A sheet within a few grey units of the page ground is a backing nobody can see — type still reads as floating. Separate the sheet from the ground decisively (e.g. `#fdfbf5` paper on an `#f3f2ea` page, at full core opacity), then let grain and shadow carry the paper feel:

- **Grain:** two `feTurbulence` fields — a fine fiber texture stretched wide, plus a slow cloud mottle — applied as a data-URI background image.
- **Lift:** `drop-shadow` applied **after** the blur in the filter chain, so the shadow follows the deckled edge instead of drawing a box around it.

## Content clears the feather, not the geometric edge

The sheet's *paper* begins well inside its *box* — the fade consumes the first N pixels. Anything positioned "on the paper" (a seal, a caption, text near an edge) must inset past the fade distance, and those insets should **derive from the fade tokens** so they move together. An element aligned to the geometric edge lands on the fade and looks like it's stamped on fog.

## Fades are smoothstep, never two-stop linear

A two-stop linear gradient starts at full slope, so where it meets a flat surface there is a slope discontinuity the eye reads as a band — **no matter how long you make the gradient**. Lengthening a linear fade does not fix the knee; only easing does. Use ~10 stops tracing `t²(3−2t)` (zero slope at both ends) so the fade has no visible beginning and no visible landing. Put the stops in px so the fade completes in a fixed distance, and floor the adjacent padding so content never lands on part-mixed ground.

## CSS traps (each cost a review round)

- **`feTurbulence` needs an explicit filter region.** `stitchTiles="stitch"` only stitches when the filter region matches the tile exactly; the default region (`-10%` … `120%`) silently doesn't, producing straight seams at the tile period. Only ~2 grey levels — but the eye picks out a straight line far below the amplitude of the surrounding grain. Always set `x='0' y='0' width='100%' height='100%'` on the filter.
- **Percentage radii in `radial-gradient` resolve against the full box, not the half-extents.** `100% 100%` builds an ellipse twice the box's size — still ~80% opaque where the box ends. For a grain-fade mask use `ellipse closest-side`. (A gradient IS allowed here — the mask carries texture, not contrast, so corner washout is the desired behavior.)
- **A fixed element crossing multiple grounds needs a halo.** A fixed rail/indicator travels over paper and over the dark colophon; give it a `drop-shadow` in a token that is always the opposite of the text color, so one halo covers both grounds in both themes.
- **Full-bleed veils, not inset boxes.** A header backing that fades out must be a full-width band with a long fade — an inset box with a short gradient shows a hard horizontal seam the moment content scrolls under it.
