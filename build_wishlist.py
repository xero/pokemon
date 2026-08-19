#!/usr/bin/env python3
"""Render the cards we want but do not have into wishlist.html.

The pull list. Same shape as collection.html, and deliberately so: the search,
the letter index, and the click-to-filter stat rows are the same controls
doing the same job, so assets/collection.js drives both pages unchanged. Only
the rows differ.

A row is here for exactly one reason: a deck's ```buy block asks for more
copies than the collection holds. Buy is the shortfall, and a card the binders
already cover does not appear at all.

quantity 0 in cards.csv is deliberately *not* the source, though it looks like
the obvious one. Most of those rows are a shortlist rather than a shopping
list: an energy-acceleration survey seeded 35 candidates into the pipeline at
once, tagged "energy accel tier 1" and "tier 2" in wanted-cards.tsv, so they
could be read and compared. They were never requested by a list, and putting
them on a page you carry into a shop turns a 25-card errand into a 71-card
one. wanted-cards.tsv keeps the reason each card was added; cards.csv does not
carry it, which is why quantity alone cannot tell the two apart.

Need sums across decks rather than taking the highest. Four Poffin in one deck
and four in another is eight cards, because both decks stay sleeved and get
played against each other; taking the max would be right only if the copies
moved between them.

Shares its data shaping with build_html.py by importing it is deliberately not
done, for the same reason that file gives: importing it writes a page.
"""
import re
from collections import Counter
from pathlib import Path

from pokelib import (CREDITS_NOTE, RARITY_SLUG, anchor, card_art, cards,
                     cost_icons, count_badge, energy_glyphs, esc, find_card,
                     icon, legal_cell, mega_sigil, page, row, stat_cell)

ROOT = Path(__file__).parent
SRC = ROOT / "cards.csv"
DEST = ROOT / "wishlist.html"

TITLE = "Pull List"

# the hoarder and the dreamer
MASCOT = ["deck"]

# md filename -> the deck's own H1, filled in as pages are named. Every .md in
# the repo is read for buy blocks rather than a list being kept in step by
# hand: a planning doc that is not built into a page still knows what it wants
# bought, and dark-smog and rocket-mewtwo are exactly that.
DECK_TITLE = {}

LABELS = [
    ("set_name", "Set"),
    ("rarity", "Rarity"),
    ("card_type", "Type"),
    ("hp", "HP"),
    ("stage", "Stage"),
    ("card_text", "Ability"),
    (None, None),
    ("weakness", "Weakness"),
    ("resistance", "Resistance"),
    ("retreat_cost", "Retreat"),
    ("standard_legal", "Tournament"),
]

LEGAL_LABEL = {
    "yes": "legal, and good to go!",
    "no": "card is too old",
    "japanese": "only English cards allowed",
    "unknown": "Unknown, check the letter on the card",
}

FILTER_KEY = {
    "set_name": "set",
    "rarity": "rarity",
    "card_type": "type",
    "stage": "stage",
    "standard_legal": "tournament",
}

TOURNAMENT = {"yes": "legal", "no": "too old", "japanese": "Japanese",
              "unknown": "unknown"}

ATTACKS = ("attack1", "attack2", "attack3", "attack4")


def key(r):
    return (r["name"], r["set_name"], r["card_number"])


def title_of(md):
    """The deck's own H1, so the page names decks the way they name themselves."""
    if md not in DECK_TITLE:
        first = (ROOT / md).read_text(encoding="utf-8").split("\n", 1)[0]
        DECK_TITLE[md] = first.lstrip("# ").strip() or md
    return DECK_TITLE[md]


def buy_blocks():
    """{card key: {md: need}}, plus notes and the lines that resolved to nothing.

    The same parse build_deck_html.buy_table does, so a line that costs out on
    a deck page costs out here identically. Two blocks in one file are one
    ask, not two, so a repeated card takes the larger of them.
    """
    wants, notes, missing = {}, {}, []
    for md in sorted(p.name for p in ROOT.glob("*.md")):
        text = (ROOT / md).read_text(encoding="utf-8")
        for block in re.findall(r"^```buy\n(.*?)^```", text, re.S | re.M):
            for line in block.splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                f = [x.strip() for x in (line.split("|") + [""] * 4)[:4]]
                query, where, need, note = f
                m = re.search(r"(\d{2,3})\s*$", where)
                r = find_card(query, re.sub(r"\d+\s*$", "", where),
                              m.group(1) if m else "")
                try:
                    want = int(need)
                except ValueError:
                    want = 0
                if not r:
                    missing.append((query, where, need, note, md))
                    continue
                k = key(r)
                # one file asking twice is one ask; across files they add up
                per = wants.setdefault(k, {})
                per[md] = max(per.get(md, 0), want)
                if note:
                    notes.setdefault(k, []).append((md, note))
    return wants, notes, missing


def value(k, r):
    v = r[k]
    if not v:
        return ""
    if k == "standard_legal":
        return legal_cell(v, esc(LEGAL_LABEL.get(v, v)))
    return stat_cell(k, r)


def attack(text):
    m = re.match(r"\[([A-Z]+)\]\s*(.*)$", text, re.S)
    if not m:
        return energy_glyphs(esc(text))
    icons = cost_icons(m.group(1))
    if not icons:
        return energy_glyphs(esc(text))
    return row(icons, energy_glyphs(esc(m.group(2))), "cost")


def stats(r):
    """Card stat rows, skipping the ones this card has nothing to say for.

    The collection can print every row because it holds Pokemon only. Here a
    Trainer sits beside a Basic Energy sits beside a Stage 2, and a column of
    dashes for HP, Stage, Weakness, Resistance and Retreat is most of what a
    Trainer would render.
    """
    out = []
    for k, label in LABELS:
        if k is None:
            out += [("Attack", attack(r[x]), "") for x in ATTACKS if r[x]]
            continue
        v = value(k, r)
        if v:
            out.append((label, v, FILTER_KEY.get(k, "")))
    return out


def tags(r):
    v = {"name": r["name"], "set": r["set_name"], "rarity": r["rarity"],
         "type": r["card_type"], "stage": r["stage"],
         "tournament": TOURNAMENT.get(r["standard_legal"], r["standard_legal"])}
    return "".join(f' data-{k}="{esc(x)}"' for k, x in v.items() if x)


# --- what belongs on the list ------------------------------------------------
wants, notes, missing = buy_blocks()
by_key = {key(r): r for r in cards()}

need = {k: sum(v.values()) for k, v in wants.items()}
own = {k: int(r["quantity"] or 0) for k, r in by_key.items()}
buy = {k: max(0, n - own.get(k, 0)) for k, n in need.items()}

keys = sorted((k for k, n in buy.items() if n > 0 and k in by_key),
              key=lambda k: (k[0].lower(), k[1], k[2]))

seen = Counter()
entries = [(by_key[k], k, anchor(by_key[k]["name"], seen)) for k in keys]

# --- navigation --------------------------------------------------------------
nav = ["<nav>", "\t<details>", "\t\t<summary>Search</summary>",
       '\t\t<input type="search" data-search placeholder="Find a card"'
       ' aria-label="Find a card" autocomplete="off" />',
       "\t\t<ul>"]
last = None
for r, k, a in entries:
    letter = r["name"][0].upper()
    if letter != last:
        nav.append(f"\t\t\t<li data-letter><b>{esc(letter)}</b></li>")
        last = letter
    n = buy.get(k, 0)
    tail = f" <em>{esc(r['set_name'])}</em>"
    nav.append(f'\t\t\t<li data-for="{a}"><a href="#{a}">{esc(r["name"])}</a>'
               f'{tail}{f" <em>buy {n}</em>" if n else ""}</li>')
nav += ["\t\t</ul>", "\t</details>", "\t<div data-active hidden></div>", "</nav>"]

# --- cards -------------------------------------------------------------------
articles = []
for r, k, a in entries:
    n = buy.get(k, 0)
    head = [mega_sigil(r["stage"], r["name"]), esc(r["name"]),
            icon("rarities", RARITY_SLUG.get(r["rarity"]), r["rarity"]),
            count_badge(n)]
    art = [f"\t\t\t<article{tags(r)}>",
           f'\t\t\t\t<h2 id="{a}">' + " ".join(p for p in head if p) + "</h2>"]
    if r["image_file"]:
        art += ["\t\t\t\t<aside>",
                "\t\t\t\t\t" + card_art(f'./assets/{r["image_file"]}', r["name"]),
                "\t\t\t\t</aside>"]
    art += ["\t\t\t\t<section>", '\t\t\t\t\t<dl class="card">']

    # the pull numbers lead, because they are the reason the card is here
    links = []
    for md, want in sorted(wants[k].items()):
        html = md.replace(".md", ".html")
        label = f"{esc(title_of(md))} <small>&times;{want}</small>"
        links.append(f'<a href="./{html}">{label}</a>'
                     if (ROOT / html).exists() else label)
    rows_ = [("Buy", f"<strong>{n}</strong>", ""),
             ("Own", str(own.get(k, 0)), ""),
             ("Need", str(need[k]), ""),
             ("Wanted by", ", ".join(links), "")]
    rows_ += [("Note", esc(note), "") for _, note in notes.get(k, [])]
    rows_ += stats(r)

    for label, v, fk in rows_:
        at = f' class="filter" data-filter="{fk}"' if fk else ""
        art.append(f"\t\t\t\t\t\t<dt{at}>{esc(label)}</dt><dd{at}>{v}</dd>")
    art += ["\t\t\t\t\t</dl>", "\t\t\t\t</section>", "\t\t\t</article>"]
    articles.append("\n".join(art))

articles.append('\t\t\t<p data-empty hidden>No cards match.</p>')

# --- footnotes ---------------------------------------------------------------
notes_out = [
    '\t\t\t<aside data-callout="note">',
    "\t\t\t\t<h2>How a card gets on this list</h2>",
    "\t\t\t\t<p>One way: a deck's buy block asks for more copies than the"
    " collection holds. <b>Buy</b> is the shortfall, so a card the binders"
    " already cover is not here at all.</p>",
    "\t\t\t\t<p>Cards nobody owns but no deck has asked for are"
    " <b>not</b> on this page. Most of them are a shortlist rather than a"
    " shopping list &mdash; the energy-acceleration survey alone seeded 35"
    " candidates into the pipeline to be read and compared. The reason each"
    " one was added lives in the note column of"
    " <code>wanted-cards.tsv</code>.</p>",
    "\t\t\t\t<p><b>Need adds up across decks.</b> Four of a card in one deck"
    " and four in another is eight, because both decks stay sleeved and get"
    " played against each other. It is not a mistake that a shared staple"
    " wants more copies than any one list does.</p>",
    "\t\t\t</aside>",
]

if missing:
    notes_out += [
        '\t\t\t<aside data-callout="warning">',
        "\t\t\t\t<h2>Wanted, but not in the pipeline yet</h2>",
        "\t\t\t\t<p>These are asked for by a buy block, but no row in"
        " <code>cards.csv</code> matches them, so there is no scan, no card"
        " text, and no price to check. Add them to"
        " <code>wanted-cards.tsv</code> and run the pipeline, and they will"
        " appear above like anything else.</p>",
        "\t\t\t\t<ul>",
    ]
    for query, where, want, note, md in missing:
        bits = f"<b>{esc(query)}</b>"
        if where:
            bits += f" <small>{esc(where)}</small>"
        if want:
            bits += f" &times;{esc(want)}"
        notes_out.append(f"\t\t\t\t\t<li>{bits} &mdash; "
                         f"<small>{esc(title_of(md))}</small></li>")
    notes_out += ["\t\t\t\t</ul>", "\t\t\t</aside>"]

notes_out.append(CREDITS_NOTE)

# --- assemble ----------------------------------------------------------------
copies = sum(buy.get(k, 0) for k in keys)
subtitle = (f"{len(entries)} cards to pull, {copies} copies in all"
            f"{f', plus {len(missing)} not in the pipeline yet' if missing else ''}.")

out = page(DEST, TITLE, subtitle, "\n\t\t\t".join(nav),
           "\n".join(articles), "\n".join(notes_out), MASCOT,
           script="./assets/collection.js")
print(f"wishlist.html: {len(entries)} cards, {copies} copies, "
      f"{len(missing)} unresolved, {len(out.splitlines())} lines, "
      f"{len(out) / 1024:.0f}kb")
