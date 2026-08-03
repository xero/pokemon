#!/usr/bin/env python3
"""Recolour the SVGs in assets/glyphs and render them to PNG.

    assets/glyphs/tcg-*.svg   ->  assets/types/<type>.png
    assets/glyphs/move-*.svg  ->  assets/moves/<move>.png

The sources are zero-licence line art with no fill attribute anywhere, so every
path falls back to the SVG default of black. fill is an inherited presentation
attribute, so setting it once on the root <svg> colours the whole glyph without
touching a single path.

Rendering to PNG rather than shipping the SVG keeps this consistent with the
rest of assets/, and sidesteps how unevenly SVG is handled when a markdown file
is read outside a browser.

These glyphs are named for TCG energy types, which is what cards.csv holds, so
no mapping between game types and card types is needed.
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
GLYPHS = ROOT / "assets" / "glyphs"
SIZE = 128

# TCG energy colours. Colorless is a mid grey so it holds against both a white
# and a dark background; it is the one that gets repeated for retreat cost.
COLOUR = {
    "grass": "#4CAF50", "fire": "#F4511E", "water": "#2196F3",
    "lightning": "#F9A825", "psychic": "#9C27B0", "fighting": "#E65100",
    "darkness": "#455A64", "metal": "#90A4AE", "fairy": "#EC407A",
    "dragon": "#B8912F", "colorless": "#9E9E9E",
}

# The damage categories are a video game idea with no TCG equivalent, so these
# are rendered for availability rather than because anything binds to them yet.
MOVE_COLOUR = "#757575"


def render(svg_path, dest, colour):
    src = svg_path.read_text(encoding="utf-8")
    if re.search(r'<svg\b[^>]*\bfill=', src):
        tinted = re.sub(r'(<svg\b[^>]*?)\bfill="[^"]*"', rf'\1fill="{colour}"',
                        src, count=1)
    else:
        tinted = re.sub(r"<svg\b", f'<svg fill="{colour}"', src, count=1)
    if tinted == src:
        print(f"  WARNING: could not set fill on {svg_path.name}", file=sys.stderr)
    tmp = svg_path.with_suffix(".tinted.tmp.svg")
    tmp.write_text(tinted, encoding="utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["magick", "-background", "none", str(tmp),
                    "-resize", f"{SIZE}x{SIZE}",
                    "-gravity", "center", "-extent", f"{SIZE}x{SIZE}",
                    f"PNG32:{dest}"], check=True)
    tmp.unlink()
    optical_align(dest, NUDGE.get(dest.stem, 0))


# Where a glyph's visual mass should begin, as a fraction of the box. Lining
# the glyphs up by their first stray pixel does not work: a fist has a flat
# left edge and lands on the line, while a star or a lightning bolt touch it
# with a single point and read as indented by comparison. So they are aligned
# on the column where the shape reaches INK_COVER of its own height instead,
# which is much closer to where the eye thinks the shape starts.
OPTICAL_LEFT = 0.05
INK_COVER = 0.25

# Hand nudges after the automatic pass, in canvas pixels. The measurement gets
# every glyph close, but a flat-edged shape still reads as sitting harder
# against the line than a round one, so the fist wants a touch more air. The
# canvas is SIZE px and renders around 20px, so roughly 6 canvas px per screen
# pixel.
NUDGE = {"fighting": 13, "colorless": 13}


def nudge_right(im, px):
    """Shift art right by px, shrinking it only if that would clip it."""
    from PIL import Image
    w, h = im.size
    bb = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if bb and px <= w - bb[2]:
        out.paste(im, (px, 0))          # room to spare, keep it full size
        return out
    scale = (w - px) / w
    small = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    out.paste(small, (px, round((h - small.height) / 2)))
    return out


def optical_align(path, nudge=0):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    a = im.getchannel("A").load()
    cols = [sum(1 for y in range(h) if a[x, y] > 16) / h for x in range(w)]
    edge = next((x for x, c in enumerate(cols) if c >= INK_COVER), None)
    if edge is None:
        return
    shift = round(OPTICAL_LEFT * w) - edge
    ink = [x for x, c in enumerate(cols) if c > 0]
    # never push the shape past the edge of its own box
    shift = max(shift, -ink[0])
    shift = min(shift, w - 1 - ink[-1])
    if shift:
        moved = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        moved.paste(im, (shift, 0))
        im = moved
    if nudge:
        im = nudge_right(im, nudge)
    if shift or nudge:
        im.save(path)


if not GLYPHS.is_dir():
    raise SystemExit(f"no glyph source at {GLYPHS}")

types = moves = 0
missing = []
for svg in sorted(GLYPHS.glob("*.svg")):
    stem = svg.stem
    if stem.startswith("tcg-"):
        name = stem[4:]
        if name not in COLOUR:
            missing.append(name)
            continue
        render(svg, ROOT / "assets" / "types" / f"{name}.png", COLOUR[name])
        types += 1
    elif stem.startswith("move-"):
        render(svg, ROOT / "assets" / "moves" / f"{stem[5:]}.png", MOVE_COLOUR)
        moves += 1

print(f"assets/types  {types} energy glyphs")
print(f"assets/moves  {moves} damage category glyphs")
if missing:
    print(f"  no colour defined for: {', '.join(missing)}")
have = {p.stem for p in (ROOT / "assets" / "types").glob("*.png")}
absent = sorted(set(COLOUR) - have)
if absent:
    print(f"  no glyph supplied for: {', '.join(absent)}")
