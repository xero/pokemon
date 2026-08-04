#!/usr/bin/env python3
"""Write index.html, the front page linking the three generated pages.

Counts are read back out of the pages themselves rather than recomputed, so
the index cannot claim a number the page it links to disagrees with.
"""
import re
from pathlib import Path

from pokelib import esc, page

ROOT = Path(__file__).parent

PAGES = [
    ("collection.html", "Every Pokémon in the binder, sorted by name, with what"
                        " each one does and whether it can be played."),
    ("fire.html", "Fox's deck, card by card: what each one is for, what it wants"
                  " to sit next to, and the game plans."),
    ("dark.html", "Xero's deck, same shape. Gengar and Weezing, and the two-turn"
                  " combo the whole thing is built around."),
]


def read(name):
    """(title, article count) straight from a built page."""
    html = (ROOT / name).read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    return title, html.count("<article>")


body, total = [], 0
for name, blurb in PAGES:
    if not (ROOT / name).exists():
        print(f"  skipping {name}, not built yet")
        continue
    title, count = read(name)
    total += count
    body += [
        "\t\t\t<article>",
        f'\t\t\t\t<h2><a href="./{name}">{title}</a></h2>',
        "\t\t\t\t<section>",
        f"\t\t\t\t\t<p>{esc(blurb)}</p>",
        f"\t\t\t\t\t<p><small>{count} cards · "
        f'<a href="./{name}">{esc(name)}</a></small></p>',
        "\t\t\t\t</section>",
        "\t\t\t</article>",
    ]

out = page(ROOT / "index.html", "Pokémon", "Deck planning for me and my son.",
           "", "\n".join(body))
print(f"index.html: {len(PAGES)} pages, {total} cards linked, "
      f"{len(out.splitlines())} lines")
