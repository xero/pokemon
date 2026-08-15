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
     "A searchable collection of our combined binders. Every card, stat, and"
     " ability, and whether it's legal for tournament play."),
    ("fire.html", ["charizard", "flareon"],
     "Fox's deck, card by card: what each one is for, what it wants to sit next"
     " to, and how to beat dad."),
    ("fire-tournament.html", ["flareon", "noctowl"],
     "Fox's tournament deck. Flareon ex, Noctowl, and why a Bench dad cannot"
     " touch changes how the whole game is played."),
    ("fire-standard.html", ["flareon-ex", "hoothoot"],
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
     "Xero's tournament deck. Mega Gengar ex over a bench of zero-prize"
     " attackers, and the prize ladder that bends every trade."),
    ("psychic-standard.html", ["chandelure", "dusknoir"],
     "Witching Hour's tournament heir. Mega Chandelure ex turns the"
     " opponent's own Retreat Cost into damage, and Boss's Orders picks"
     " the victim."),
    ("eevee-standard.html", ["eevee-ex", "umbreon"],
     "Fox's Eevee deck, and the only one here that is two decks. Fifty"
     " cards never move; ten swap between Sun and Moon for home and Fire"
     " and Ice for game night."),
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
    # split on the tag name, not on "<article>": the collection's articles
    # carry the filter values as attributes, and matching the bare tag counted
    # every one of them as zero
    cards = sum(1 for a in re.split(r"<article\b", html)[1:]
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
