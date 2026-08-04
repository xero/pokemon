#!/usr/bin/env python3
"""Write index.html, the front page linking the three generated pages.

Counts are read back out of the pages themselves rather than recomputed, so
the index cannot claim a number the page it links to disagrees with.
"""
import re
from pathlib import Path

from pokelib import CREDITS_NOTE, esc, page

ROOT = Path(__file__).parent

PAGES = [
    ("collection.html", ["charizard-mega-x", "gengar-mega"],
     "Every Pokémon in the binder, sorted by name, with what each one does, and"
     " if it's tournament legal."),
    ("fire.html", ["charizard", "flareon"],
     "Fox's deck, card by card: what each one is for, what it wants to sit next"
     " to, and how to beat dad."),
    ("fire-tournament.html", ["flareon", "noctowl"],
     "Fox's tournament deck. Flareon ex, Noctowl, and why a Bench dad cannot"
     " touch changes how the whole game is played."),
    ("fire-standard.html", ["flareon", "hoothoot"],
     "The planning notes behind the Flareon Engine: why the deck is built this"
     " way, the exact card text, and what it still gives up."),
    ("dark.html", ["gengar", "weezing"],
     "Xero's deck. The dark duo of Gengar and Weezing, and the two-turn combo"
     " dad's whole deck is built around."),
    ("psychic-lanterns.html", ["chandelure", "gengar-mega-shiny"],
     "Paper plan. Chandelure dropping three damage counters anywhere on the"
     " board, every turn, for free — including on the Bench."),
    ("psychic-sleep.html", ["hypno", "drowzee"],
     "Paper plan. The other way to build the Psychic Gengars: put them to"
     " sleep on turn one and never let them wake up."),
    ("dark-ex.html", ["gengar-mega", "gengar-mega-shiny"],
     "Not a deck, a primer. Mega Gengar ex and the cards around it, used to"
     " explain how ex play style actually works."),
]


def read(name):
    """(title, card count) straight from a built page.

    Counting every <article> overstated it: on a deck page the word list and
    the game plans are articles too, which had fire.html claiming 38 unique
    cards for a 20-card list. A real card page is the one carrying a stat
    block, so that is what gets counted.
    """
    html = (ROOT / name).read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    cards = sum(1 for a in html.split("<article>")[1:]
                if "How many" in (body := a.split("</article>")[0])
                or 'class="card"' in body)
    return title, cards


body, total = [], 0
for name, sprites, blurb in PAGES:
    if not (ROOT / name).exists():
        print(f"  skipping {name}, not built yet")
        continue
    title, count = read(name)
    total += count
    art = ["\t\t\t<article>"]
    # decorative, and the heading right beside them already names the page
    gifs = [s for s in sprites
            if (ROOT / "assets" / "sprites" / f"{s}.gif").exists()]
    if gifs:
        tags = "".join(f'<img src="./assets/sprites/{s}.gif" alt="" />'
                       for s in gifs)
        art.append(f"\t\t\t\t<aside data-sprite>{tags}</aside>")
    # the heading lives inside the section so the sprite can sit beside it
    # rather than being pushed under a full-width row
    art += [
        "\t\t\t\t<section>",
        f'\t\t\t\t\t<h2><a href="./{name}">{title}</a></h2>',
        f"\t\t\t\t\t<p>{esc(blurb)}</p>",
    ]
    # the planning docs have no card pages to count, so they get no count line
    # rather than an honest-looking "0 unique cards"
    if count:
        art.append(f"\t\t\t\t\t<p><small><em>{count} unique cards</em></small></p>")
    art += ["\t\t\t\t</section>", "\t\t\t</article>"]
    body += art

out = page(ROOT / "index.html", "Pokémon TCG",
           "Deck planning for me and my son.",
           "", "\n".join(body), CREDITS_NOTE)
print(f"index.html: {len(PAGES)} pages, {total} cards linked, "
      f"{len(out.splitlines())} lines")
