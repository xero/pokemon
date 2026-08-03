#!/usr/bin/env python3
"""Download rarity symbols and set graphics from pokesymbols.com into assets/.

Files are saved under the set's own slug, the one in its page URL, so a lookup
from a set name lands on a predictable filename.

That slug is not always the slug of the image. Black Star Promo sets all share
one graphic called _promo, and many Japanese sets use a name unrelated to their
page URL. So each set is tried at the obvious path first, and when that 404s its
detail page is fetched and the real <img> src is read off it. The index pages
cannot supply this on their own: they lazy-load, so their markup only carries
the handful of tiles that happened to render.

    assets/rarities/     rarity symbols
    assets/sets/         English set symbols, the small icon on a card
    assets/set-logos/    English set logos, the full wordmark
    assets/sets-jp/      Japanese set symbols

Not every set publishes both a symbol and a logo, so confirmed 404s are counted
rather than treated as errors. Existing files are skipped, so reruns are cheap
and safe.
"""
import re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
SITE = "https://pokesymbols.com"
ATTEMPTS = 4

# section page, image directory, image kind, destination folder
SOURCES = [
    ("/tcg/sets", "/images/tcg/sets/symbols", "symbols", "sets"),
    ("/tcg/sets", "/images/tcg/sets/logos", "logos", "set-logos"),
    ("/tcg/japanese-sets", "/images/tcg/japanese-sets/symbols", "symbols", "sets-jp"),
]


def curl(url, dest=None):
    cmd = ["curl", "-sL", "--max-time", "40"]
    if dest:
        cmd += ["-o", str(dest), "-w", "%{http_code}"]
    return subprocess.run(cmd + [url], capture_output=True, text=True).stdout


def download(url, dest):
    """True on success, False once a 404 is confirmed. Retries anything else."""
    for i in range(ATTEMPTS):
        code = curl(url, dest)
        if code == "200" and dest.exists() and dest.stat().st_size > 0:
            return True
        dest.unlink(missing_ok=True)
        if code == "404":
            return False
        time.sleep(2 * 2 ** i)
    return False


def real_src(page, kind):
    """The full image path this set uses, read off its detail page.

    Both the directory and the filename can differ from the guess. Older
    Japanese sets live under /images/low-res/ rather than /images/tcg/, and
    Black Star Promo sets all point at one shared file called _promo. So the
    whole path is taken from the page rather than assembled from parts.

    kind is "symbols" or "logos"; a set's page carries both when it has both.
    """
    html = curl(SITE + page)
    m = re.search(r'/images/[a-z0-9/_\-]*?' + re.escape(kind) + r'/[a-z0-9_\-]+\.png',
                  html)
    return m.group(0) if m else None


# --- rarities: the index lists these as plain images, no detail pages ---------
out = ASSETS / "rarities"
out.mkdir(parents=True, exist_ok=True)
html = curl(SITE + "/tcg/rarities")
rarities = sorted(set(re.findall(r"/images/tcg/rarities/([a-z0-9\-]+)\.png", html)))
got = skipped = 0
for s in rarities:
    dest = out / f"{s}.png"
    if dest.exists() and dest.stat().st_size > 0:
        skipped += 1
    elif download(f"{SITE}/images/tcg/rarities/{s}.png", dest):
        got += 1
print(f"assets/rarities   {got} downloaded, {skipped} already had "
      f"({len(rarities)} rarities)", file=sys.stderr)

# --- sets --------------------------------------------------------------------
slug_cache = {}
for page, imgdir, kind, folder in SOURCES:
    if page not in slug_cache:
        html = curl(SITE + page)
        slug_cache[page] = sorted(set(re.findall(
            re.escape(f'href="{page}/') + r'([a-z0-9\-]+)"', html)))
    slugs = slug_cache[page]

    out = ASSETS / folder
    out.mkdir(parents=True, exist_ok=True)
    got = skipped = absent = indirect = 0
    for s in slugs:
        dest = out / f"{s}.png"
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        if download(f"{SITE}{imgdir}/{s}.png", dest):
            got += 1
        else:
            alt = real_src(f"{page}/{s}", kind)
            if alt and download(SITE + alt, dest):
                got += 1
                indirect += 1
            else:
                absent += 1
        time.sleep(0.3)
    print(f"assets/{folder:<12}{got:>4} downloaded ({indirect} via detail page), "
          f"{skipped:>4} already had, {absent:>4} not published "
          f"of {len(slugs)}", file=sys.stderr)

# --- graphics from elsewhere -------------------------------------------------
# pokesymbols has no entry for the Trick or Trade Halloween bundles, which are a
# real part of this collection. dextcg publishes the Pikachu jack-o'-lantern
# stamp those cards carry. Fetched as webp and converted so it matches the rest.
EXTRA = {
    "sets/trick-or-trade.png":
        "https://static.dextcg.com/resources/variants/TrickOrTradeVariant.webp",
    # The rarities index has no Promo entry, but promo cards do print a rarity
    # and TCGplayer reports it as "Promo". The Black Star Promo mark those cards
    # carry is the same graphic the promo sets use, so it is copied in here to
    # sit alongside the other rarity symbols.
    "rarities/promo.png": SITE + "/images/tcg/sets/symbols/_promo.png",
}

for rel, url in EXTRA.items():
    dest = ASSETS / rel
    if dest.exists() and dest.stat().st_size > 0:
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".src")
    if download(url, tmp):
        subprocess.run(["magick", str(tmp), "-resize", "600x600",
                        "-background", "none", "-gravity", "center",
                        "-extent", "600x600", f"PNG32:{dest}"], check=True)
        tmp.unlink()
        print(f"assets/{rel} fetched and converted", file=sys.stderr)
    else:
        print(f"WARNING: could not fetch {url}", file=sys.stderr)

# --- crop away the transparent margin ----------------------------------------
# The symbols ship letterboxed into a square canvas. The modern set plates are
# the worst of it: 584x304 of artwork centred in 600x600, so 51% of the file is
# empty. Since the page sizes these by height, that padding is rendered as
# blank space and the artwork comes out half the size it should be.
#
# Cropping to the alpha bounding box is safe and idempotent: a tight graphic
# has a bbox equal to its canvas and is left alone, and re-running finds
# nothing left to trim.
CROP_FOLDERS = ["rarities", "sets", "set-logos", "sets-jp"]


def autocrop(path):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    bb = im.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
    if not bb or bb == (0, 0, im.width, im.height):
        return False
    im.crop(bb).save(path)
    return True


cropped = 0
for folder in CROP_FOLDERS:
    for suffix in ("", "-dark"):
        d = ASSETS / (folder + suffix)
        if not d.exists():
            continue
        n = sum(autocrop(f) for f in sorted(d.glob("*.png")))
        cropped += n
        if n:
            print(f"assets/{folder + suffix:<18}{n:>4} cropped", file=sys.stderr)

# --- dark-theme variants -----------------------------------------------------
# Most of these graphics are black line art on transparency, which disappears
# against a dark background. They are monochrome, so inverting RGB and keeping
# alpha turns the black ink white and leaves the shape alone. Colour graphics
# are left untouched: inverting those would wreck their hues, and they are
# legible on a dark background already.
#
# The test is how much dark ink the image contains, not how dark it is on
# average. Averages lie on line art: the Promo mark is a black star holding
# white lettering and averages out to a middling 152, yet 40% of it is black
# and that 40% is exactly what vanishes on a dark background.
SAT_MONO = 25       # mean channel spread, below which it counts as monochrome
INK_DARK = 60       # luminance at or below which a pixel counts as dark ink
INK_SHARE = 0.20    # share of visible pixels that must be dark ink


def make_dark(src, dst):
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    px = list(im.getdata())
    vis = [(r, g, b) for r, g, b, a in px if a > 32]
    if not vis:
        return False
    sat = sum(max(c) - min(c) for c in vis) / len(vis)
    if sat >= SAT_MONO:
        return False
    ink = sum(1 for r, g, b in vis
              if 0.299 * r + 0.587 * g + 0.114 * b <= INK_DARK) / len(vis)
    if ink < INK_SHARE:
        return False
    im.putdata([(255 - r, 255 - g, 255 - b, a) for r, g, b, a in px])
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)
    return True


made = 0
for folder in ("rarities", "sets", "set-logos", "sets-jp"):
    src_dir = ASSETS / folder
    if not src_dir.exists():
        continue
    n = 0
    for f in sorted(src_dir.glob("*.png")):
        dst = ASSETS / f"{folder}-dark" / f.name
        if dst.exists():
            continue
        if make_dark(f, dst):
            n += 1
    made += n
    if n:
        print(f"assets/{folder}-dark  {n} inverted for dark theme", file=sys.stderr)

print("done")
for folder in ("rarities", "sets", "set-logos", "sets-jp"):
    for suffix in ("", "-dark"):
        d = ASSETS / (folder + suffix)
        if d.exists():
            print(f"  assets/{folder + suffix:<18}{len(list(d.glob('*.png'))):>4} files")
