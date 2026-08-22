#!/usr/bin/env python3
"""Cut a Chinese seal (印章) from 小篆 glyph outlines or a seal-script font.

Pipeline (per real 篆刻 practice):
  render each glyph -> trim to ink -> stretch-fit into its cell (屈曲填满:
  seals legitimately distort glyphs to fill) -> thicken PER GLYPH to a target
  ink density (疏密匀称: sparse characters get fatter strokes so every cell
  carries equal visual mass) -> draw 界格 rules + border -> structured 残破
  wear (破边 bites, 残断 notches, 印泥不匀 blotching; see WEAR_LEVELS) ->
  noise-erode the silhouette so it reads as carved stone -> potrace to one
  clean SVG path.

Usage:
    python3 cut_seal.py --text 上善若水 --glyph-dir ./glyphs \
        [--font /path/to/seal-font.ttf] [--layout auto|single|column|name|grid] \
        [--style zhuwen|baiwen] [--color '#c6472e'] [--out ./out] \
        [--wear none|light|medium|heavy|<0-100>] [--seed <int>]

Glyph source per character: `<glyph-dir>/<char>-seal.svg` if present
(fetch with fetch_glyph.py), else rendered from --font if given.
Output: `seal.svg` (fill="currentColor", color-agnostic) plus `seal-preview.png`
(the seal in --color on a paper ground) in --out.

Deps: Pillow, ImageMagick (`magick`), `potrace`, and `rsvg-convert` for SVG
glyphs (all in Homebrew / apt).
"""

import argparse
import math
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFilter, ImageFont

RENDER_PX = 900       # per-glyph render resolution
CELL = 460            # nominal cell edge at working resolution
PAPER = "#f3f2ea"     # preview ground
INSET, BORDER, RULE = 34, 38, 16   # frame geometry shared by every layout

# 残破 (wear): real seals are used stones. Named levels; an integer 0-100 is
# also accepted. Icon/favicon-size cuts should take none or light — at tiny
# sizes chipping reads as noise, not age.
WEAR_LEVELS = {"none": 0, "light": 25, "medium": 50, "heavy": 75}


def die(msg: str) -> None:
    sys.exit(f"cut_seal: {msg}")


def require(*tools: str) -> None:
    missing = [t for t in tools if shutil.which(t) is None]
    if missing:
        die(f"missing required tools: {', '.join(missing)} (install via Homebrew/apt)")


# --- glyph rendering ---------------------------------------------------------

def render_svg_glyph(svg: Path, out_dir: Path) -> Image.Image:
    png = out_dir / f"_glyph-{svg.stem}.png"
    subprocess.run(
        ["rsvg-convert", "-w", str(RENDER_PX), "-h", str(RENDER_PX),
         "--background-color", "white", "-o", str(png), str(svg)],
        check=True,
    )
    return trim_ink(Image.open(png).convert("L"), svg.name)


def render_font_glyph(char: str, font_path: Path) -> Image.Image:
    font = ImageFont.truetype(str(font_path), int(RENDER_PX * 0.9))
    im = Image.new("L", (RENDER_PX, RENDER_PX), 255)
    draw = ImageDraw.Draw(im)
    draw.text((RENDER_PX // 2, RENDER_PX // 2), char, font=font, fill=0, anchor="mm")
    return trim_ink(im, f"{char} (font)")


def trim_ink(im: Image.Image, label: str) -> Image.Image:
    """Dark-on-light bitmap -> white-ink-on-black, cropped to the ink bbox."""
    ink = im.point(lambda p: 255 if p < 128 else 0)
    bbox = ink.getbbox()
    if not bbox:
        die(f"{label}: rendered blank — wrong file, or font lacks this glyph")
    return ink.crop(bbox)


def load_glyph(char: str, glyph_dir: Path, font: Path | None, out_dir: Path) -> Image.Image:
    svg = glyph_dir / f"{char}-seal.svg"
    if svg.exists():
        return render_svg_glyph(svg, out_dir)
    if font is not None:
        return render_font_glyph(char, font)
    die(f"no glyph for {char}: {svg} missing and no --font given "
        f"(run fetch_glyph.py first, or supply a seal-script font)")


# --- composition -------------------------------------------------------------

def ink_ratio(im: Image.Image) -> float:
    return im.histogram()[255] / float(im.width * im.height)


def fit_glyph(glyph: Image.Image, cell, pad_ratio=0.055, target_ink=0.33,
              max_grow=26) -> tuple[Image.Image, tuple[int, int]]:
    x0, y0, x1, y1 = cell
    px, py = int((x1 - x0) * pad_ratio), int((y1 - y0) * pad_ratio)
    tw, th = max(x1 - x0 - 2 * px, 1), max(y1 - y0 - 2 * py, 1)
    g = glyph.resize((tw, th), Image.LANCZOS).point(lambda p: 255 if p > 110 else 0)
    for _ in range(max_grow):
        if ink_ratio(g) >= target_ink:
            break
        g = g.filter(ImageFilter.MaxFilter(3))
    return g, (x0 + px, y0 + py)


def layout_cells(layout: str, n: int, rule: int, field):
    """Return (canvas_w, canvas_h is fixed by caller) cell boxes in READING
    order (top->bottom, right column before left) plus 界格 rule segments."""
    f0x, f0y, f1x, f1y = field
    g = rule // 2 + 5
    if layout == "single":
        return [(f0x + 4, f0y + 4, f1x - 4, f1y - 4)], []
    if layout == "column":
        step = (f1y - f0y) / n
        cells = [(f0x + 4, int(f0y + i * step) + (g if i else 4),
                  f1x - 4, int(f0y + (i + 1) * step) - (g if i < n - 1 else 4))
                 for i in range(n)]
        rules = [("h", int(f0y + i * step)) for i in range(1, n)]
        return cells, rules
    if layout == "name":  # 3 chars: first full-height right, 2nd/3rd stacked left
        mx, my = (f0x + f1x) // 2, (f0y + f1y) // 2
        cells = [(mx + g, f0y + 4, f1x - 4, f1y - 4),
                 (f0x + 4, f0y + 4, mx - g, my - g),
                 (f0x + 4, my + g, mx - g, f1y - 4)]
        return cells, [("v", mx), ("hl", my)]
    if layout == "grid":  # 4 chars: right column top/bottom, then left column
        mx, my = (f0x + f1x) // 2, (f0y + f1y) // 2
        cells = [(mx + g, f0y + 5, f1x - 5, my - g),
                 (mx + g, my + g, f1x - 5, f1y - 5),
                 (f0x + 5, f0y + 5, mx - g, my - g),
                 (f0x + 5, my + g, mx - g, f1y - 5)]
        return cells, [("v", mx), ("h", my)]
    die(f"unknown layout '{layout}'")


def compose(text: str, layout: str, glyphs: list[Image.Image], style: str):
    n = len(text)
    inset, border, rule = INSET, BORDER, RULE
    if layout == "single":
        w = h = 1000
    elif layout == "column":
        w, h = 620, 2 * (inset + border) + n * CELL
    else:
        w, h = 1300, 1560
    canvas = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(canvas)
    field = (inset + border, inset + border, w - inset - border, h - inset - border)
    cells, rules = layout_cells(layout, n, rule, field)

    if style == "zhuwen":
        # red strokes on paper: ink(white) = border + rules + glyph strokes
        draw.rectangle([inset, inset, w - inset - 1, h - inset - 1],
                       outline=255, width=border)
        for kind, pos in rules:
            if kind == "h":
                draw.rectangle([field[0], pos - rule // 2, field[2], pos + rule // 2], fill=255)
            elif kind == "v":
                draw.rectangle([pos - rule // 2, field[1], pos + rule // 2, field[3]], fill=255)
            elif kind == "hl":  # horizontal rule on left half only (name layout)
                draw.rectangle([field[0], pos - rule // 2, (field[0] + field[2]) // 2,
                                pos + rule // 2], fill=255)
        for glyph, cell in zip(glyphs, cells):
            g, at = fit_glyph(glyph, cell)
            canvas.paste(g, at, g)
    else:
        # 白文: red block, strokes cut away to paper. Slightly fatter strokes
        # read better as negative space.
        draw.rectangle([inset, inset, w - inset - 1, h - inset - 1], fill=255)
        for glyph, cell in zip(glyphs, cells):
            g, at = fit_glyph(glyph, cell, target_ink=0.38, max_grow=30)
            black = Image.new("L", g.size, 0)
            canvas.paste(black, at, g)

    return canvas.filter(ImageFilter.MaxFilter(3)) if style == "zhuwen" else canvas


# --- 残破 wear ----------------------------------------------------------------

def jagged_blob(rng: random.Random, cx, cy, rx, ry, rot=0.0, n=16):
    """Irregular polygon around (cx, cy); vertex radius swings 0.45..1.35x."""
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 0.45 + rng.random() * 0.9
        x, y = math.cos(a) * rx * r, math.sin(a) * ry * r
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def draw_bite(draw, rng, cx, cy, tang, nx, ny, level, scale, border):
    """One 破边 event: lobes walking a jittery crack path along the band,
    never one smooth blob, plus detached debris flecks."""
    base = scale * (24 + level * 0.42)
    tvx, tvy = abs(ny), abs(nx)              # unit tangent of this side
    dir_sign = rng.choice((-1, 1))
    sx, sy = cx, cy
    for _ in range(rng.randint(3, 6)):
        rx = base * (0.5 + rng.random() * 0.65)
        ry = min(border * (0.75 + rng.random() * 0.85),
                 rx * (0.8 + rng.random() * 0.6))
        wob = (rng.random() - 0.5) * border * 0.9
        draw.polygon(jagged_blob(rng, sx + nx * wob, sy + ny * wob,
                                 rx, ry, tang + rng.uniform(-0.25, 0.25)), fill=0)
        adv = base * (0.55 + rng.random() * 0.7) * dir_sign
        sx += tvx * adv
        sy += tvy * adv
    for _ in range(rng.randint(1, 4)):
        fx = sx + tvx * rng.uniform(-1.4, 1.4) * base \
            + nx * rng.uniform(-1.6, 1.6) * border
        fy = sy + tvy * rng.uniform(-1.4, 1.4) * base \
            + ny * rng.uniform(-1.6, 1.6) * border
        fr = base * (0.12 + rng.random() * 0.22)
        draw.polygon(jagged_blob(rng, fx, fy, fr * 1.5, fr,
                                 rng.uniform(0, math.pi), n=9), fill=0)


def edge_gnaw(canvas: Image.Image, rng: random.Random, level: int,
              scale: float) -> Image.Image:
    """Pit every ink edge at two granularities — stone grain, not vector."""
    w, h = canvas.size
    band = ImageChops.subtract(canvas.filter(ImageFilter.MaxFilter(5)),
                               canvas.filter(ImageFilter.MinFilter(5)))
    for cell_px, density in ((max(int(3 * scale), 2), 0.05 + level / 100 * 0.10),
                             (max(int(7 * scale), 3), 0.03 + level / 100 * 0.09)):
        grid = Image.new("L", (w // cell_px + 1, h // cell_px + 1))
        grid.putdata([255 if rng.random() < density else 0
                      for _ in range(grid.width * grid.height)])
        noise = grid.resize((w, h), Image.NEAREST)
        canvas = ImageChops.subtract(canvas, ImageChops.multiply(band, noise))
    return canvas


def wear(canvas: Image.Image, rng: random.Random, level: int,
         frame: tuple[int, int]) -> Image.Image:
    """Structured 残破 on the clean mask; level 0-100, frame=(inset, border).

    Runs on the clean binary mask BEFORE carve()'s uniform grain:
      破边     — composite crack-path bites straddling the border band, with
                 detached debris flecks
      残断     — jagged notches punched into glyph/rule strokes
      印泥不匀  — low-frequency blotch map thinning ink like uneven pressure
    plus edge_gnaw(). All geometry scales off the canvas long edge."""
    if level <= 0:
        return canvas
    w, h = canvas.size
    inset, border = frame
    draw = ImageDraw.Draw(canvas)
    scale = max(w, h) / 1300.0               # constants tuned at the grid canvas

    sides = [  # (orientation, centerline coord, t range, tangent, inward normal)
        ("h", inset + border / 2, inset, w - inset, 0.0, (0, 1)),
        ("h", h - inset - border / 2, inset, w - inset, math.pi, (0, -1)),
        ("v", inset + border / 2, inset, h - inset, math.pi / 2, (1, 0)),
        ("v", w - inset - border / 2, inset, h - inset, -math.pi / 2, (-1, 0)),
    ]
    for _ in range(1 + int(level / 40)):     # 破边 bites across the band
        kind, fixed, t0, t1, tang, nrm = sides[rng.randrange(4)]
        span = t1 - t0
        if rng.random() < 0.35:              # corner chips read naturally
            t = t0 + span * rng.choice((0.06, 0.94)) \
                + rng.uniform(-span * .05, span * .05)
        else:
            t = t0 + span * rng.uniform(0.15, 0.85)
        cx, cy = (fixed, t) if kind == "h" else (t, fixed)
        draw_bite(draw, rng, cx, cy, tang, nrm[0], nrm[1], level, scale, border)

    f0 = inset + border                      # 残断 stroke notches in the field
    field = canvas.crop((f0, f0, w - f0, h - f0))
    ds = 4
    small = field.resize((max(field.width // ds, 1), max(field.height // ds, 1)),
                         Image.NEAREST)
    px = small.load()
    ink_pts = [(x, y) for y in range(small.height) for x in range(small.width)
               if px[x, y] > 127]
    placed, want = [], max(1, round(level / 9))
    for _ in range(want * 3):
        if len(placed) >= want or not ink_pts:
            break
        qx, qy = ink_pts[rng.randrange(len(ink_pts))]
        cx, cy = f0 + qx * ds + rng.uniform(-ds, ds), f0 + qy * ds + rng.uniform(-ds, ds)
        if any((cx - ox) ** 2 + (cy - oy) ** 2 < (46 * scale) ** 2 for ox, oy in placed):
            continue
        placed.append((cx, cy))
        rn = scale * (7 + rng.random() * 12) * (0.75 + level / 250)
        draw.polygon(jagged_blob(rng, cx, cy, rn, rn, rng.uniform(0, math.pi), n=12),
                     fill=0)

    canvas = edge_gnaw(canvas, rng, level, scale)

    amp = int(150 * level / 100)             # 印泥不匀 blotchy thinning
    gw, gh = max(w // 14, 2), max(h // 14, 2)
    grid = Image.new("L", (gw, gh))
    grid.putdata([rng.randint(0, 255) for _ in range(gw * gh)])
    blotch = grid.resize((w, h), Image.BILINEAR).filter(
        ImageFilter.GaussianBlur(radius=int(26 * scale)))
    return ImageChops.subtract(canvas, blotch.point(lambda p: p * amp // 255))


def resolve_wear(spec: str):
    """'none'|'light'|'medium'|'heavy' or an integer 0-100 -> level int."""
    if spec in WEAR_LEVELS:
        return WEAR_LEVELS[spec]
    try:
        level = int(spec)
    except ValueError:
        die(f"unknown --wear '{spec}' (use none|light|medium|heavy or 0-100)")
    if not 0 <= level <= 100:
        die("--wear integer must be 0-100")
    return level


# --- carve + trace -----------------------------------------------------------

def carve(clean: Path, carved: Path, attenuate: float) -> None:
    subprocess.run(
        ["magick", str(clean), "-colorspace", "gray", "-attenuate", str(attenuate),
         "+noise", "Gaussian", "-blur", "0x1.6", "-threshold", "48%", str(carved)],
        check=True,
    )


def trace(carved: Path, svg_out: Path, label: str) -> None:
    pbm = carved.with_suffix(".pbm")
    subprocess.run(["magick", str(carved), "-negate", "-threshold", "50%", str(pbm)],
                   check=True)
    raw = carved.with_name(carved.stem + "-raw.svg")
    subprocess.run(["potrace", str(pbm), "--svg", "--alphamax", "1.0",
                    "--opttolerance", "0.6", "--turdsize", "4", "-o", str(raw)],
                   check=True)
    src = raw.read_text()
    vb = re.search(r'viewBox="([^"]+)"', src).group(1).split()
    body = re.search(r"(<g .*?</g>)", src, re.S).group(1)
    body = body.replace('fill="#000000"', 'fill="currentColor"').replace(' stroke="none"', "")
    svg_out.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {float(vb[2]):.0f} {float(vb[3]):.0f}" '
        f'fill="currentColor" role="img" aria-label="{label}">\n{body}\n</svg>\n'
    )


def preview(carved: Path, out_png: Path, color: str) -> None:
    ink = Image.open(carved).convert("L")
    rgb = ImageColor.getrgb(color)
    base = Image.new("RGB", ink.size, ImageColor.getrgb(PAPER))
    base.paste(Image.new("RGB", ink.size, rgb), (0, 0), ink)
    pad = int(min(ink.size) * 0.18)
    framed = Image.new("RGB", (ink.width + 2 * pad, ink.height + 2 * pad),
                       ImageColor.getrgb(PAPER))
    framed.paste(base, (pad, pad))
    framed.save(out_png)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", required=True, help="seal text, 1-8 characters")
    ap.add_argument("--glyph-dir", default="./glyphs")
    ap.add_argument("--font", default=None, help="seal-script font fallback (ttf/otf)")
    ap.add_argument("--layout", default="auto",
                    choices=["auto", "single", "column", "name", "grid"])
    ap.add_argument("--style", default="zhuwen", choices=["zhuwen", "baiwen"])
    ap.add_argument("--color", default="#c6472e", help="preview color (cinnabar default)")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--wear", default="light",
                    help="残破 wear: none|light|medium|heavy or 0-100 (default light)")
    ap.add_argument("--seed", default=None,
                    help="wear RNG seed; default derives from text+style+layout, "
                         "so recuts of the same seal are identical")
    args = ap.parse_args()

    require("magick", "potrace", "rsvg-convert")
    n = len(args.text)
    if not 1 <= n <= 8:
        die("text must be 1-8 characters")
    layout = args.layout
    if layout == "auto":
        layout = {1: "single", 3: "name", 4: "grid"}.get(n, "column")
    if layout == "name" and n != 3:
        die("name layout needs exactly 3 characters")
    if layout == "grid" and n != 4:
        die("grid layout needs exactly 4 characters")
    if layout == "single" and n != 1:
        die("single layout needs exactly 1 character")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    font = Path(args.font) if args.font else None
    glyphs = [load_glyph(c, Path(args.glyph_dir), font, out_dir) for c in args.text]

    level = resolve_wear(args.wear)
    canvas = compose(args.text, layout, glyphs, args.style)
    if level > 0:
        seed = args.seed if args.seed is not None \
            else f"zhuanke/{args.text}/{args.style}/{layout}"
        canvas = wear(canvas.copy(), random.Random(seed), level, (INSET, BORDER))
        print(f"wear: level {level}, seed {seed!r}")
    clean = out_dir / "seal-clean.png"
    canvas.save(clean)
    carved = out_dir / "seal-carved.png"
    carve(clean, carved, attenuate=3.0)
    svg = out_dir / "seal.svg"
    trace(carved, svg, f"{args.text} seal")
    png = out_dir / "seal-preview.png"
    preview(carved, png, args.color)
    print(f"cut: {svg} ({svg.stat().st_size} bytes), preview: {png}")


if __name__ == "__main__":
    main()
