#!/usr/bin/env python3
"""Download type and damage icons from HybridShivam/Pokemon into assets/.

    assets/types/              type icons, recoloured per TCG energy colour
    assets/types-svg/          the untouched source SVGs
    assets/damage-categories/  Physical / Special / Status, grey and white
    assets/misc/               Mega Evolution sigil

The type SVGs are a single path filled white, so recolouring is a string swap.
They are rendered to PNG afterwards because a PNG renders the same everywhere,
which matters for a file read on GitHub.

Note the icons are named for the video game types. This is a TCG collection, so
Lightning wants the electric icon, Darkness the dark one, Colorless the normal
one, and Metal the steel one. build_collection.py holds that mapping.
"""
import re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
RAW = "https://raw.githubusercontent.com/HybridShivam/Pokemon/master/assets/Others"
SIZE = 128
ATTEMPTS = 3

TYPES = ["bug", "dark", "dragon", "electric", "fairy", "fighting", "fire",
         "flying", "ghost", "grass", "ground", "ice", "normal", "poison",
         "psychic", "rock", "steel", "water"]

# TCG energy colours, not the video game palette. Colorless is a mid grey so it
# holds up against both a white and a dark background.
COLOUR = {
    "grass": "#4CAF50", "fire": "#F4511E", "water": "#2196F3",
    "electric": "#F9A825", "psychic": "#9C27B0", "fighting": "#E65100",
    "dark": "#455A64", "steel": "#90A4AE", "fairy": "#EC407A",
    "dragon": "#B8912F", "normal": "#9E9E9E",
    # types with no TCG energy of their own keep a sensible game-ish colour
    "bug": "#A6B91A", "flying": "#8E7BEF", "ghost": "#735797",
    "ground": "#C7912F", "ice": "#5FC7C7", "poison": "#A33EA1",
    "rock": "#B6A136",
}

DAMAGE = ["Physical", "Physical-white", "Special", "Special-white",
          "Status", "Status-white"]


def fetch(url, dest):
    for i in range(ATTEMPTS):
        code = subprocess.run(
            ["curl", "-sL", "--max-time", "40", "-o", str(dest),
             "-w", "%{http_code}", url],
            capture_output=True, text=True).stdout
        if code == "200" and dest.exists() and dest.stat().st_size > 0:
            return True
        dest.unlink(missing_ok=True)
        if code == "404":
            return False
        time.sleep(2 * 2 ** i)
    return False


svg_dir = ASSETS / "types-svg"
png_dir = ASSETS / "types"
for d in (svg_dir, png_dir, ASSETS / "damage-categories", ASSETS / "misc"):
    d.mkdir(parents=True, exist_ok=True)

got = failed = []
got, failed = 0, []
for t in TYPES:
    svg = svg_dir / f"{t}.svg"
    if not svg.exists() and not fetch(f"{RAW}/type-icons/{t}.svg", svg):
        failed.append(f"type-icons/{t}.svg")
        continue
    png = png_dir / f"{t}.png"
    if png.exists():
        continue
    # The shape is one path filled white, but the file spells that as either
    # "white" or "#fff". fill="none" is the empty <svg> backdrop; leave it.
    src = svg.read_text(encoding="utf-8")
    tinted, hits = re.subn(r'fill="(?:white|#fff(?:fff)?)"',
                           f'fill="{COLOUR.get(t, "#9E9E9E")}"', src,
                           flags=re.IGNORECASE)
    if not hits:
        print(f"  WARNING: nothing to recolour in {t}.svg", file=sys.stderr)
    tmp = svg_dir / f".{t}.tinted.svg"
    tmp.write_text(tinted, encoding="utf-8")
    subprocess.run(["magick", "-background", "none", str(tmp),
                    "-resize", f"{SIZE}x{SIZE}", f"PNG32:{png}"], check=True)
    tmp.unlink()
    got += 1
print(f"assets/types            {got} recoloured, {len(TYPES)} types", file=sys.stderr)

n = 0
for name in DAMAGE:
    dest = ASSETS / "damage-categories" / f"{name}.png"
    if dest.exists():
        continue
    if fetch(f"{RAW}/damage-category-icons/64h/{name}.png", dest):
        n += 1
    else:
        failed.append(f"damage-category-icons/64h/{name}.png")
print(f"assets/damage-categories {n} downloaded", file=sys.stderr)

dest = ASSETS / "misc" / "mega-evolution-sigil.png"
if not dest.exists():
    if fetch(f"{RAW}/Mega-Evolution-Sigil.png", dest):
        print("assets/misc             mega-evolution-sigil.png", file=sys.stderr)
    else:
        failed.append("Mega-Evolution-Sigil.png")

print("done")
for d in ("types", "types-svg", "damage-categories", "misc"):
    p = ASSETS / d
    print(f"  assets/{d:<20}{len(list(p.iterdir())):>4} files")
if failed:
    print("  could not fetch:", ", ".join(failed))
