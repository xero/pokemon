#!/usr/bin/env python3
"""Build deal.html, a prototype of the deck list dealing itself out.

Not part of build.py, and not registered in decks.toml: it is a UI sketch,
run by hand after a change to assets/deal/. The page is the shared template
with its own stylesheet and script in the HEAD and SCRIPT slots, the same
way the damage calculator is built.

The deck list is lifted straight out of overgrowth.html rather than rebuilt
from the markdown, so it is the real strip with the real markup: the scans,
the count badges, and the links, which are pointed back at the card sections
on the Overgrowth page. The Bling Deck showcase at the foot of that page is
lifted too, and each scan carries its rare print's url in data-bling-src,
so the $$$ can turn the strip over to the other art without leaving it. If
the strip's markup changes in build_deck_html.py, rebuilding Overgrowth and
then this page picks it up.
"""
import hashlib, re
from pathlib import Path

from pokelib import CREDITS_NOTE, page

ROOT = Path(__file__).parent
SRC = ROOT / "overgrowth.html"
OUT = ROOT / "assets" / "deal"
DEST = ROOT / "deal.html"

TITLE = "Deal"
MASCOT = ["meganium", "venusaur-mega"]
BACK = "./assets/calc/card-back.png"

FIGURE = re.compile(r'<figure><a href="(#[^"]+)"><img src="([^"]+)"')


def stamp(path):
    """?v= from the file's own bytes, so a phone never runs new HTML against
    a cached old script, and an unchanged file keeps its URL."""
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


def strips():
    """Every deck-list strip on the Overgrowth page, as lists of lines.

    The first [data-decklist] on that page is the deck list itself; the
    second is the Bling Deck showcase, whose art is remote.
    """
    html = SRC.read_text(encoding="utf-8")
    found = re.findall(r"<article data-decklist>\n(.*?)\n\t*</article>", html,
                       re.S)
    if len(found) < 2:
        raise SystemExit(f"{SRC.name}: need the deck list and its showcase")
    return [[ln.strip() for ln in block.splitlines() if ln.strip()]
            for block in found]


def strip():
    """The deck list, re-indented, each scan carrying its rare print.

    A card with two rare prints in the showcase (Mega Venusaur ex, Dawn)
    gets the first; the strip has one figure per card, and so does the
    swap.
    """
    deck, showcase = strips()[:2]
    bling = {}
    for ln in showcase:
        m = FIGURE.search(ln)
        if m and m.group(1) not in bling:
            bling[m.group(1)] = m.group(2)
    out, missing = [], []
    for ln in deck:
        m = FIGURE.search(ln)
        if m and m.group(1) in bling:
            # the img is the first void tag on the line
            ln = ln.replace(" />", f' data-bling-src="{bling[m.group(1)]}" />', 1)
        elif m:
            missing.append(m.group(1))
        # the thumbnails link to the card sections on the Overgrowth page
        out.append(ln.replace('href="#', 'href="./overgrowth.html#'))
    for a in missing:
        print(f"  no rare print for {a}; it keeps its own scan")
    return "\n".join("\t\t\t\t\t" + ln for ln in out)


def body(figures):
    return f"""\t\t\t<aside data-callout="note">
\t\t\t\t<p><strong>What this page is for.</strong></p>
\t\t\t\t<p>A UI prototype, linked from nowhere. The deck list below is the <a href="./overgrowth.html">Overgrowth</a> sixty, exactly as that page draws it, with one script on top: the cards start in a stack in the middle (on a phone, in the corner), face down, get shuffled, slide to the corner, get dealt out to their places in the grid, and turn face up. Hover a card once it is dealt.</p>
\t\t\t\t<p>The <b>$$$</b> in the corner of the Deck List heading is the Bling Deck: every card turns face down, the pile rebuilds in the middle (on a phone, in the corner), gets shuffled, slides back to the corner, and the deal runs again with the rare prints. Press it again for the regular ones.</p>
\t\t\t\t<p>Scroll the list out of view and back to run the whole thing again, or use the controls to run the deal again.</p>
\t\t\t</aside>
\t\t\t<section data-controls>
\t\t\t\t<h3>Controls</h3>
\t\t\t\t<form>
\t\t\t\t\t<label>
\t\t\t\t\t\t<span>Deal from</span>
\t\t\t\t\t\t<select name="origin">
\t\t\t\t\t\t\t<option value="top-left">Top left</option>
\t\t\t\t\t\t\t<option value="center">The middle</option>
\t\t\t\t\t\t\t<option value="top-right">Top right</option>
\t\t\t\t\t\t\t<option value="bottom-left">Bottom left</option>
\t\t\t\t\t\t\t<option value="bottom-right">Bottom right</option>
\t\t\t\t\t\t\t<option value="above">Off the top of the screen</option>
\t\t\t\t\t\t</select>
\t\t\t\t\t</label>
\t\t\t\t\t<label>
\t\t\t\t\t\t<span>Turn over</span>
\t\t\t\t\t\t<select name="flip">
\t\t\t\t\t\t\t<option value="ripple">Rippling out from the pile</option>
\t\t\t\t\t\t\t<option value="order">In the order dealt</option>
\t\t\t\t\t\t\t<option value="random">In no order</option>
\t\t\t\t\t\t\t<option value="once">All at once</option>
\t\t\t\t\t\t</select>
\t\t\t\t\t</label>
\t\t\t\t\t<label>
\t\t\t\t\t\t<span>Speed</span>
\t\t\t\t\t\t<select name="speed">
\t\t\t\t\t\t\t<option value="0.5">Half</option>
\t\t\t\t\t\t\t<option value="1">Normal</option>
\t\t\t\t\t\t\t<option value="1.5">Brisk</option>
\t\t\t\t\t\t\t<option value="2">Double</option>
\t\t\t\t\t\t</select>
\t\t\t\t\t</label>
\t\t\t\t\t<button type="button" data-replay>Deal again</button>
\t\t\t\t</form>
\t\t\t</section>
\t\t\t<section>
\t\t\t\t<h3 id="deck-list">Deck List<button type="button" data-bling aria-pressed="false" title="Bling Deck">$$$</button></h3>
\t\t\t\t<article data-decklist data-deal-back="{BACK}">
{figures}
\t\t\t\t</article>
\t\t\t</section>"""


def main():
    css = OUT / "deal.css"
    js = OUT / "deal.js"
    subtitle = ("The Overgrowth deck list, dealt from a stack and turned face "
                "up. A UI prototype.")
    out = page(DEST, TITLE, subtitle, "", body(strip()), CREDITS_NOTE, MASCOT,
               script=f"./assets/deal/deal.js?v={stamp(js)}",
               head=(f'<link rel="stylesheet" '
                     f'href="./assets/deal/deal.css?v={stamp(css)}" />'))
    cards = out.count("<figure>")
    print(f"deal.html: {cards} cards, {len(out.splitlines())} lines")


if __name__ == "__main__":
    main()
