#!/usr/bin/env python3
"""Render the Pokemon in cards.csv into collection.html, one article per card.

The standalone build. build_markdown.py still produces collection.md for
reading on GitHub; this one exists because GitHub's markdown pipeline keeps
getting in the way, and because a page we control can lay the cards out for a
phone instead of forcing a desktop-width table.

Layout comes from assets/template.html, which carries the whole stylesheet in
its head so the output is one file plus images. Every card is an <article>
holding a heading, an <aside> for the scan, and a <section> of stats in a <dl>.
Flex wrap does the responsive work, so the two columns fold into one on a narrow
screen without a breakpoint deciding it.

Shares its data shaping with build_markdown.py by importing it is deliberately
not done: that module writes a file on import. The overlap is small and the two
targets want different markup.
"""
import csv, re
from collections import Counter
from pathlib import Path

from pokelib import (ASSETS, COST_TYPE, CREDITS_NOTE, RARITY_SLUG, anchor,
                     cost_icons, esc, group, icon, img, mega_sigil, page, row,
                     set_folder, set_slug, type_icon, typed)

ROOT = Path(__file__).parent
SRC = ROOT / "cards.csv"
TEMPLATE = ROOT / "assets" / "template.html"
DEST = ROOT / "collection.html"

TITLE = "Pokémon Caught!"

# Sprites shown beside the title.
MASCOT = ["gengar-mega", "charizard"]

# CSV column -> term shown in the <dl>. None means the value is self-describing
# and stands without one. The attacks slot expands to one row per attack.
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
    "yes": ("ok", "legal, and good to go!"),
    "no": ("no", "card is too old"),
    "japanese": ("no", "only English cards allowed"),
    "unknown": ("unown", "Unknown, check the letter on the card"),
}

ATTACKS = ("attack1", "attack2", "attack3", "attack4")
MARKS_ANCHOR = "checking-the-letter"

EXAMPLE_PAIR = (
    ("Charmander", "SWSH04: Vivid Voltage"),
    ("Charmander", "ME02: Phantasmal Flames"),
)

NOT_POKEMON = ("Trainer", "Energy")


def value(key, r):
    v = r[key]
    if not v:
        return "&ndash;"
    if key == "set_name":
        folder = set_folder(r.get("product_line"))
        return row(icon(folder, set_slug(v), v),
                   esc(v) + f' <small>{esc(r["card_number"])}</small>')
    if key == "rarity":
        return row(icon("rarities", RARITY_SLUG.get(v), v), esc(v))
    if key in ("card_type", "weakness", "resistance"):
        return typed(v)
    if key == "retreat_cost":
        n = int(v) if v.isdigit() else 0
        return row(type_icon("Colorless") * n, esc(v), "cost")
    if key == "standard_legal":
        badge, text = LEGAL_LABEL.get(v, ("", v))
        ico = ""
        if badge and (ROOT / "assets" / f"{badge}.png").exists():
            ico = img(f"./assets/{badge}.png", badge.upper())
        if v == "unknown":
            text += f' <a href="#{MARKS_ANCHOR}">*</a>'
            return row(ico, text)
        return row(ico, esc(text))
    if key == "card_text":
        v = re.sub(r"^Ability:\s*", "", v)
    return esc(v)


def attack(text):
    """An attack with its leading energy cost swapped for glyphs."""
    m = re.match(r"\[([A-Z]+)\]\s*(.*)$", text, re.S)
    if not m:
        return esc(text)
    icons = cost_icons(m.group(1))
    return row(icons, esc(m.group(2)), "cost") if icons else esc(text)


def stats(r):
    out = []
    for key, label in LABELS:
        if key is None:
            out += [("Attack", attack(r[k])) for k in ATTACKS if r[k]]
        else:
            out.append((label, value(key, r)))
    return out


rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8"))
        if not r["card_type"].startswith(NOT_POKEMON)]
rows.sort(key=lambda r: (r["name"].lower(), r["set_name"], r["card_number"]))

if any(not r["hp"] or not r["stage"] for r in rows):
    raise SystemExit("a kept row has no hp or stage; the Pokemon filter is wrong")

seen = Counter()
entries = [(r, anchor(r["name"], seen)) for r in rows]

# --- navigation --------------------------------------------------------------
# Letter markers are list items too: <ul> only ever admits <li> children.
nav = ["<nav>", "\t<details>", "\t\t<summary>Pokédex</summary>", "\t\t<ul>"]
last = None
for r, a in entries:
    letter = r["name"][0].upper()
    if letter != last:
        nav.append(f"\t\t\t<li><b>{esc(letter)}</b></li>")
        last = letter
    nav.append(f'\t\t\t<li><a href="#{a}">{esc(r["name"])}</a> '
               f'<em>{esc(r["set_name"])}</em></li>')
nav += ["\t\t</ul>", "\t</details>", "</nav>"]

# --- cards -------------------------------------------------------------------
articles = []
for r, a in entries:
    head = [mega_sigil(r["stage"], r["name"]), esc(r["name"]),
            icon("rarities", RARITY_SLUG.get(r["rarity"]), r["rarity"])]
    art = ["\t\t\t<article>",
           f'\t\t\t\t<h2 id="{a}">' + " ".join(p for p in head if p) + "</h2>"]
    if r["image_file"]:
        art += ["\t\t\t\t<aside>",
                "\t\t\t\t\t" + img(f'./assets/{r["image_file"]}', r["name"]),
                "\t\t\t\t</aside>"]
    art += ["\t\t\t\t<section>", '\t\t\t\t\t<dl class="card">']
    for label, v in stats(r):
        art.append(f"\t\t\t\t\t\t<dt>{esc(label)}</dt><dd>{v}</dd>")
    art += ["\t\t\t\t\t</dl>", "\t\t\t\t</section>", "\t\t\t</article>"]
    articles.append("\n".join(art))

# --- footnotes ---------------------------------------------------------------
notes = [
    f'\t\t\t<aside data-callout="important" id="{MARKS_ANCHOR}">',
    "\t\t\t\t<h2>* Checking the letter</h2>",
    "\t\t\t\t<p>Every modern card has a tiny letter printed in the bottom"
    " corner, next to the card number. That letter is the only thing that"
    " decides whether a card is too old to play. The set it came from does not"
    " decide it, and neither does how new the card looks.</p>",
    "\t\t\t\t<p>Right now three letters are legal: <b>H</b>, <b>I</b>, and"
    " <b>J</b>.</p>",
    "\t\t\t\t<p><b>G and anything older rotated out</b> on"
    ' <time datetime="2026-04-10">10 April 2026</time>. A card with no letter'
    " at all is older still, so it is out too.</p>",
    "\t\t\t</aside>",
    '\t\t\t<aside data-callout="warning">',
    "\t\t\t\t<h2>Same name, different card</h2>",
    "\t\t\t\t<p>Two cards can share a name and still be completely different"
    " cards. One can have an Ability the other does not. The attacks can cost"
    " different Energy and do different damage. The name on the card is not the"
    " card.</p>",
]

by_card = {(r["name"], r["set_name"]): (r, a) for r, a in entries}
pair = [by_card.get(k) for k in EXAMPLE_PAIR]
if all(pair):
    (r1, a1), (r2, a2) = pair

    def sketch(r):
        bits = ["an <b>Ability</b>" if r["card_text"] else "no Ability"]
        atk = [r[k] for k in ATTACKS if r[k]]
        if atk:
            bits.append(f"{len(atk)} attack" + ("s" if len(atk) > 1 else ""))
        return " and ".join(bits)

    notes += [
        f'\t\t\t\t<p>Comparing <a href="#{a1}">{esc(r1["name"])},'
        f' {esc(r1["set_name"])}</a> and <a href="#{a2}">{esc(r2["name"])},'
        f' {esc(r2["set_name"])}</a> side by side:</p>',
        "\t\t\t\t<ul>",
        f'\t\t\t\t\t<li>The {esc(r1["set_name"])} one has {sketch(r1)}.</li>',
        f'\t\t\t\t\t<li>The {esc(r2["set_name"])} one has {sketch(r2)}.</li>',
        "\t\t\t\t</ul>",
        "\t\t\t\t<p>One of those is in your deck and one is legal today, and"
        " they are still not the same card.</p>",
    ]

notes += ["\t\t\t\t<p>Read the one in your hand every time.</p>",
          "\t\t\t</aside>", CREDITS_NOTE]

# --- assemble ----------------------------------------------------------------
legal = sum(1 for r in rows if r["standard_legal"] == "yes")
subtitle = f"{len(rows)} Pok&eacute;mon, {legal} of them tournament legal."

out = page(DEST, TITLE, subtitle, "\n\t\t\t".join(nav),
           "\n".join(articles), "\n".join(notes), MASCOT)
print(f"collection.html: {len(rows)} entries, {legal} legal, "
      f"{len(out.splitlines())} lines, {len(out) / 1024:.0f}kb")
