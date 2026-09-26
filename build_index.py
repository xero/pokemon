#!/usr/bin/env python3
"""Write index.html, the front page linking every published page.

What is listed, in what order, under which heading, and with what sprites and
blurb all come from decks.toml. The library pages lead with no heading, then
League Decks, then Other Decks with a subheading per group. Everything above
Other Decks carries data-featured, which the template tints.

Counts are read back out of the pages themselves rather than recomputed, so
the index cannot claim a number the page it links to disagrees with.
"""
import re
from pathlib import Path

from decklib import load, published
from pokelib import CREDITS_NOTE, esc, page

ROOT = Path(__file__).parent

SHELVES = [("league", "League Decks"), ("other", "Other Decks")]


def layout():
    """The front page top to bottom: heading strings and (page, sprites, blurb).

    A string is a heading, and its hashes are its level, same as the markdown.
    Every page after it takes the next level down for its title. Groups keep
    the order their first deck appears in, so reordering the file reorders the
    page.
    """
    library, decks = load()
    out = [(e["page"], e["sprites"], e["blurb"]) for e in published(library)]
    for shelf, title in SHELVES:
        rows = [d for d in published(decks) if d["shelf"] == shelf]
        if not rows:
            continue
        out.append(f"## {title}")
        group = None
        for d in rows:
            if d.get("group") and d["group"] != group:
                group = d["group"]
                out.append(f"### {group}")
            out.append((d["page"], d["sprites"], d["blurb"]))
    return out


PAGES = layout()
OTHER = "## Other Decks"


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
level = 2   # a page title sits one level under the last heading, h2 before any
featured = True
for entry in PAGES:
    if isinstance(entry, str):
        featured = featured and entry != OTHER
        hashes, text = entry.split(" ", 1)
        body.append(f"\t\t\t<h{len(hashes)}>{esc(text)}</h{len(hashes)}>")
        level = len(hashes) + 1
        continue
    name, sprites, blurb = entry
    if not (ROOT / name).exists():
        print(f"  skipping {name}, not built yet")
        continue
    title, count = read(name)
    total += count
    art = ['\t\t\t<article class="index" data-featured>' if featured
           else '\t\t\t<article class="index">']
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
        f'\t\t\t\t\t<h{level}><a href="./{name}">{title}</a></h{level}>',
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
           "", "\n".join(body), CREDITS_NOTE, back="")
pages = sum(1 for e in PAGES if not isinstance(e, str))
print(f"index.html: {pages} pages, {total} cards linked, "
      f"{len(out.splitlines())} lines")
