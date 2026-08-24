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

## 洒金 — gold flecks in the paper

洒金宣 is a real paper: cut gold foil sprinkled onto the sheet while the size is still wet. That sentence is the *entire* justification for gold on a page whose palette allows one hot color, and it only holds while the foil reads as **material**. Flecks mark nothing, mean nothing, carry no gloss, and never sit beside a control. **The day they read as yellow sparkle they have become a second accent color, and the fix is to delete them, not retune them.**

- **On cream paper, gold is a DARK color.** This is the counterintuitive one and it costs a round if you miss it. A wide alpha range — on the theory that varying opacity reads as light catching foil at different angles — renders as **pale beige crumbs**: measured, the strongest pixel came out `(209,189,142)`, which is warm paper, not metal. Beige is light-and-warm; gold is mid-dark, warm **and** saturated. Use a **narrow, high alpha range** (floor ≈0.62) and a saturated mid-dark value, and let flake **size** carry the variety instead. That is also the truer model: every flake on a sheet is cut from the same foil and differs only in how big a piece landed.
- **Flakes are torn, not round.** Angular convex polygons, 4–7 straight edges, squashed on one axis and spun. Circles read as confetti or as a particle shader.
- **The scatter clumps.** A hand throwing gold does not produce a Poisson field: place most flakes in a handful of gaussian "throws" with a thin uniform drift between them. An even scatter reads as a CSS texture, which is the thing this is trying not to be.
- **Wrap the tile toroidally.** Re-emit every flake within its own radius of an edge on the opposite edge, so the tile repeats with no seam and no sliced flake.
- **Two coprime periods off one asset.** Paint the same tile twice, the second rescaled ~1.3× and offset: one request buys a second flake size *and* a second repeat period. Choose **prime** tile dimensions so the layers cannot realign inside any page. Verify by autocorrelating the fleck field down a tall strip — peaks should appear only at the two designed periods and nowhere else. This matters more than it does for grain: grain seams are ~2 grey levels and still read as a grid, and a gold flake is far louder than that.
- **Paint it as a mask over `background-color`, not as a picture.** Same technique as a seal chop: the flecks then inherit each theme's own metal token instead of baking a hex, so light and dark share one asset. A dark theme wants gold that *lifts* off the ground (磁青纸泥金 — gold sutras on indigo paper) and at lower density, because a light mark on a dark ground carries much further than a dark one on a light ground.
- **It scrolls with the paper, never with the viewport.** Gold fixed to the viewport is glitter on a screen, not foil in a sheet.
- **The trade-off is real and cannot be tuned away — state it.** Gold convincing enough to be gold is dark enough to cost contrast where a flake lands under a glyph, and a gold pale enough to clear AA under *muted* text is beige. Land body copy above the AA floor against the **strongest possible fleck** (mask alpha 1 at the shipped dial) and pin that arithmetic in a test — it is invisible in a screenshot. Accept the muted-text case on the grounds that a fleck is a few pixels of texture rather than a background (coverage ≈0.12% of a frame), and keep the number written down.
- **Give it one dial.** A single opacity token, like the ink floor for a background wash. It should move the strongest fleck monotonically *toward the ground in both themes*, so turning gold down always raises worst-case contrast; at zero the paper is plain again and nothing else has to move.

## Content clears the feather, not the geometric edge

The sheet's *paper* begins well inside its *box* — the fade consumes the first N pixels. Anything positioned "on the paper" (a seal, a caption, text near an edge) must inset past the fade distance, and those insets should **derive from the fade tokens** so they move together. An element aligned to the geometric edge lands on the fade and looks like it's stamped on fog.

## Fades are smoothstep, never two-stop linear

A two-stop linear gradient starts at full slope, so where it meets a flat surface there is a slope discontinuity the eye reads as a band — **no matter how long you make the gradient**. Lengthening a linear fade does not fix the knee; only easing does. Use ~10 stops tracing `t²(3−2t)` (zero slope at both ends) so the fade has no visible beginning and no visible landing. Put the stops in px so the fade completes in a fixed distance, and floor the adjacent padding so content never lands on part-mixed ground.

## CSS traps (each cost a review round)

- **`feTurbulence` needs an explicit filter region.** `stitchTiles="stitch"` only stitches when the filter region matches the tile exactly; the default region (`-10%` … `120%`) silently doesn't, producing straight seams at the tile period. Only ~2 grey levels — but the eye picks out a straight line far below the amplitude of the surrounding grain. Always set `x='0' y='0' width='100%' height='100%'` on the filter.
- **Percentage radii in `radial-gradient` resolve against the full box, not the half-extents.** `100% 100%` builds an ellipse twice the box's size — still ~80% opaque where the box ends. For a grain-fade mask use `ellipse closest-side`. (A gradient IS allowed here — the mask carries texture, not contrast, so corner washout is the desired behavior.)
- **A fixed element crossing multiple grounds needs a halo.** A fixed rail/indicator travels over paper and over the dark colophon; give it a `drop-shadow` in a token that is always the opposite of the text color, so one halo covers both grounds in both themes.
- **Full-bleed veils, not inset boxes.** A header backing that fades out must be a full-width band with a long fade — an inset box with a short gradient shows a hard horizontal seam the moment content scrolls under it.
- **`file://` silently blocks external SVG masks.** A `mask-image: url(thing.svg)` harness opened from the filesystem renders *nothing at all*, with no console error and no visible failure — it just looks like your mask is empty. Serve mask harnesses over http. (Related: measuring a page inside an iframe needs the iframe to be **same-origin**, or `contentDocument` is null and the probe returns nothing; a different port is a different origin.)
- **A `z-index: -1` pseudo only clears its own element's background if that element creates a stacking context.** `position: relative` with `z-index: auto` does **not** create one, so the pseudo joins the nearest ancestor's context and paints *below* its own element's background — where any opaque background on that element covers it completely. Add `isolation: isolate`. This is the standard way to put paper texture, grain, or flecks above an element's ground but below all of its content, and it fails silently: the layer is simply invisible.
- **An opaque section background covers the sheet's material.** A section that paints its own ground (a colophon ramp, a tinted band) hides the page-level grain underneath it, so texture stops dead at that section and restarts after it. If the material must run continuously, restore it *on that section*, masked with **the section background's own gradient stops** — as the ground covers grain by `a`, the restore layer adds it back by `a` and the two sum to a constant. They are then one gradient written twice; changing one without the other reopens the seam.
- **Match the geometry of adjacent texture layers exactly.** A full-bleed grain meeting an inset, side-feathered grain steps by several grey levels at the join near the page margins — one measured −6.94, nearly twice the amplitude already ruled a visible seam. Same width, same feather, same opacity: then no vertical fade is needed at all.
- **Never emit non-ASCII through `perl`/`sed` escapes.** `\x97` writes the CP1252 em-dash byte, not UTF-8's `E2 80 94`. One invalid byte anywhere in a stylesheet makes the browser **drop everything after it** — in a real incident that silently deleted an entire dark theme defined near the end of the file, while the page still rendered and every test still passed (Node's `readFileSync(…, 'utf8')` substitutes U+FFFD rather than throwing, so string assertions keep matching). Write the character directly, and guard it: decode the **raw bytes** of every shipped text file with `new TextDecoder('utf-8', { fatal: true })`. To report *where*, scan with `{ stream: true }` — a one-shot decode of each prefix throws on any legitimate multi-byte character and will point at the file's first CJK byte instead.
- **Capture fixed-position art at the size it will really be viewed.** The obvious way to check a long page is one tall screenshot — a 1440×8000 window. But a `position: fixed` background (the living ink, a wash, a canvas) then becomes *8000px tall*, so its gradient and its density match nothing a reader will ever see. This produced two confident, entirely phantom findings in one session: "the foot is 13 grey levels darker than the sheet" and "the dark theme's links are unreadable". Both evaporated when the same states were captured at 1440×900 with the inner document scrolled instead. Screenshot at real viewport size and scroll; use the tall capture only for layout geometry, never for colour or contrast.
- **Verify a texture by measuring it, not by looking.** A fleck field, a fade, and a laid-line pattern all fail in ways a screenshot hides. Diff the page against itself with the feature's dial at zero to isolate exactly its contribution; autocorrelate down a strip to find repeats; take a first-difference profile across a fade to expose the knee. Every one of these found a defect that eyeballing had passed.
