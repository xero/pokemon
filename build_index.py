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
    ("dark.html", ["gengar", "weezing"],
     "Xero's deck. The dark duo of Gengar and Weezing, and the two-turn combo"
     " dad's whole deck is built around."),
]


def read(name):
    """(title, article count) straight from a built page."""
    html = (ROOT / name).read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    return title, html.count("<article>")


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
        f"\t\t\t\t\t<p><small><em>{count} unique cards</em></small></p>",
        "\t\t\t\t</section>",
        "\t\t\t</article>",
    ]
    body += art

out = page(ROOT / "index.html", "Pokémon TCG",
           "Deck planning for me and my son.",
           "", "\n".join(body), CREDITS_NOTE)
print(f"index.html: {len(PAGES)} pages, {total} cards linked, "
      f"{len(out.splitlines())} lines")
