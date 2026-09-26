#!/usr/bin/env python3
"""Render the pull list, wishlist.html: every card we still have to buy.

Same shape as collection.html, and deliberately so: the search, the letter
index, and the click-to-filter stat rows are the same controls doing the same
job, so assets/collection.js drives both pages unchanged. Only the rows differ.

A card is here for exactly one reason: its owned flag in product-ids.tsv is 0.
Nothing is counted, scraped, or inferred. Every card is owned unless someone
says otherwise, and add_cards.py --need is how someone says it.

How many to buy comes from the deck lists, the Qty tables in each deck's
markdown, and it is one deck per player. Xero sleeves one of his decks and Fox
sleeves one of his, so two of Xero's decks asking for four Poffin need four:
the copies move between them. A Fox deck asking for four too makes eight,
because his deck and Xero's get sleeved on the same night and played against
each other. Draft decks count, since a card is usually bought for a deck
before that deck is published; the page names them without a link.

Shares its data shaping with build_html.py by importing it is deliberately not
done, for the same reason that file gives: importing it writes a page.
"""
import re
from collections import Counter
from pathlib import Path

from decklib import card_key, deck_cards, load
from pokelib import (CREDITS_NOTE, RARITY_SLUG, anchor, card_art, cards,
                     cost_icons, count_badge, energy_glyphs, esc, icon,
                     legal_cell, mega_sigil, page, row, stat_cell)

ROOT = Path(__file__).parent
SRC = ROOT / "cards.csv"
DEST = ROOT / "wishlist.html"

TITLE = "Pull List"

# the hoarder and the dreamer
MASCOT = ["deck"]

# md filename -> the deck's own H1, filled in as decks are named
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


def title_of(md):
    """The deck's own H1, so the page names decks the way they name themselves."""
    if md not in DECK_TITLE:
        first = (ROOT / md).read_text(encoding="utf-8").split("\n", 1)[0]
        DECK_TITLE[md] = first.lstrip("# ").strip() or md
    return DECK_TITLE[md]


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
LIBRARY, DECKS = load()
PLAYER = {d["source"]: d["player"] for d in DECKS}
LIVE = {d["source"] for d in DECKS if not d["draft"]}

# {card key: {deck md: copies}} across every registered deck, drafts included
wants = {}
for d in DECKS:
    for k, copies in deck_cards(d["source"]).items():
        wants.setdefault(k, {})[d["source"]] = copies


def need_of(per):
    """Copies to buy, from {md: copies}: the largest ask on each side, added."""
    return sum(max((n for md, n in per.items() if PLAYER[md] == who), default=0)
               for who in ("xero", "fox"))


rows = sorted((r for r in cards() if r.get("owned") == "0"),
              key=lambda r: (r["name"].lower(), r["set_name"], r["card_number"]))
buy = {card_key(r): need_of(wants.get(card_key(r), {})) for r in rows}

seen = Counter()
entries = [(r, card_key(r), anchor(r["name"], seen)) for r in rows]

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
    for md, copies in sorted(wants.get(k, {}).items()):
        html = md.replace(".md", ".html")
        label = f"{esc(title_of(md))} <small>&times;{copies}</small>"
        links.append(f'<a href="./{html}">{label}</a>' if md in LIVE
                     else f"{label} <small>(draft)</small>")
    # one <span> round the list: the <dd> is a flex row, and loose text and
    # tags inside it each become a flex item that drops its spaces, which ran
    # the deck names together as "Dogs ×4,Gengar Gang ×3"
    rows_ = [("Buy", f"<strong>{n}</strong>" if n else "no deck lists it yet", ""),
             ("Wanted by", f"<span>{', '.join(links) or '&ndash;'}</span>", "")]
    rows_ += stats(r)

    for label, v, fk in rows_:
        at = f' class="filter" data-filter="{fk}"' if fk else ""
        art.append(f"\t\t\t\t\t\t<dt{at}>{esc(label)}</dt><dd{at}>{v}</dd>")
    art += ["\t\t\t\t\t</dl>", "\t\t\t\t</section>", "\t\t\t</article>"]
    articles.append("\n".join(art))

# --- footnotes ---------------------------------------------------------------
notes_out = [
    '\t\t\t<aside data-callout="note">',
    "\t\t\t\t<h2>How a card gets on this list</h2>",
    "\t\t\t\t<p>One way: it is marked as not owned. Every card is owned"
    " unless someone says otherwise, so nothing lands here by accident, and"
    " nothing is counted or guessed. <code>add_cards.py --need</code> puts a"
    " card on the list and <code>--have</code> takes it off.</p>",
    "\t\t\t\t<p><b>Buy is one deck per player.</b> Xero sleeves one of his"
    " decks and Fox sleeves one of his, so four of a card in two of Xero's"
    " decks is four, not eight. A card both of us run adds up: four in"
    " Xero's deck and four in Fox's is eight, because those two decks get"
    " sleeved on the same night.</p>",
    "\t\t\t</aside>",
    CREDITS_NOTE,
]

# --- assemble ----------------------------------------------------------------
copies = sum(buy.values())
if entries:
    subtitle = f"{len(entries)} cards to pull, {copies} copies in all."
    articles.append('\t\t\t<p data-empty hidden>No cards match.</p>')
    nav_html, script = "\n\t\t\t".join(nav), "./assets/collection.js"
else:
    # nothing to search and nothing to filter, so no search box and no script
    subtitle = "Nothing to pull."
    articles = ['\t\t\t<p data-empty>Every card is in the binders. Mark one'
                ' as not owned and it lands here.</p>']
    nav_html, script = "", ""

out = page(DEST, TITLE, subtitle, nav_html, "\n".join(articles),
           "\n".join(notes_out), MASCOT, script=script)
print(f"wishlist.html: {len(entries)} cards, {copies} copies, "
      f"{len(out.splitlines())} lines, {len(out) / 1024:.0f}kb")
