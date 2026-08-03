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
import csv, html, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "cards.csv"
TEMPLATE = ROOT / "assets" / "template.html"
DEST = ROOT / "collection.html"

TITLE = "Pokémon Caught!"

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

SET_SLUG = {
    "Base Set": "base",
    "EX Crystal Guardians": "crystal-guardians",
    "Pokémon GO": "pokemon-go",
    "SV: Scarlet & Violet 151": "151",
    "SWSH01: Sword & Shield Base Set": "sword-and-shield",
    "SWSH: Sword & Shield Promo Cards": "swsh-black-star-promos",
    "Trick or Trade BOOster Bundle": "trick-or-trade",
    "Trick or Trade BOOster Bundle 2023": "trick-or-trade",
    "Trick or Trade BOOster Bundle 2024": "trick-or-trade",
    "MBG: MEGA Starter Set Mega Gengar ex": "megagengar",
}

RARITY_SLUG = {
    "Common": "common", "Uncommon": "uncommon", "Rare": "rare",
    "Holo Rare": "rare", "Double Rare": "double-rare",
    "Ultra Rare": "ultra-rare", "ACE SPEC Rare": "ace-spec-rare",
    "Promo": "promo", "Art Rare": "illustration-rare",
}

TYPES = {"Colorless", "Darkness", "Dragon", "Fairy", "Fighting", "Fire",
         "Grass", "Lightning", "Metal", "Psychic", "Water"}

# Attack costs print as energy symbols on the card, so they render as glyphs
# here rather than as a bracket of letters.
COST_TYPE = {"G": "Grass", "R": "Fire", "W": "Water", "L": "Lightning",
             "P": "Psychic", "F": "Fighting", "D": "Darkness", "M": "Metal",
             "Y": "Fairy", "N": "Dragon", "C": "Colorless"}

NOT_POKEMON = ("Trainer", "Energy")


def esc(s):
    return html.escape(str(s or ""))


def img(src, alt, extra=""):
    return f'<img src="{src}" alt="{esc(alt)}"{extra} />'


def group(icons, kind=""):
    """Wrap a row's leading glyphs so they can be aligned as a column.

    Two flavours. The default is a fixed-width box with its single glyph
    centred, so set, rarity, type, weakness, resistance and tournament all line
    up regardless of how wide each individual symbol is. "cost" is for rows
    with a variable number of symbols, which start at the same left edge and
    run as wide as they need.
    """
    if not icons:
        return ""
    attr = ' data-icons="cost"' if kind == "cost" else " data-icons"
    return f"<span{attr}>{icons}</span>"


def row(icons, text, kind=""):
    """A value cell: leading glyphs, then the text in its own box.

    The text is boxed so that when it wraps, the later lines line up under the
    first one rather than running back beneath the icons.
    """
    return group(icons, kind) + f"<span>{text}</span>"


def icon(folder, slug, alt):
    """An inline graphic, wrapped in <picture> when a dark variant exists."""
    if not slug:
        return ""
    for f in ((folder, "set-logos") if folder == "sets" else (folder,)):
        if not (ROOT / "assets" / f / f"{slug}.png").exists():
            continue
        tag = img(f"./assets/{f}/{slug}.png", alt)
        if (ROOT / "assets" / f"{f}-dark" / f"{slug}.png").exists():
            return ('<picture><source media="(prefers-color-scheme: dark)" '
                    f'srcset="./assets/{f}-dark/{slug}.png" />{tag}</picture>')
        return tag
    return ""


def type_icon(tcg_type):
    if tcg_type not in TYPES:
        return ""
    slug = tcg_type.lower()
    if not (ROOT / "assets" / "types" / f"{slug}.png").exists():
        return ""
    return img(f"./assets/types/{slug}.png", tcg_type)


def typed(v):
    return row(type_icon(v.split(" ")[0]), esc(v))


def set_slug(name):
    if name in SET_SLUG:
        return SET_SLUG[name]
    s = re.sub(r"^[A-Z][A-Z0-9]{1,5}\s*[:\-]\s*", "", name)
    return re.sub(r"[^a-z0-9]+", "-", s.replace("&", "and").lower()).strip("-")


def set_folder(product_line):
    return "sets-jp" if "japan" in (product_line or "").lower() else "sets"


def mega_sigil(r):
    if not (r["stage"].lower().startswith("mega")
            or r["name"].lower().startswith("mega ")):
        return ""
    if not (ROOT / "assets" / "glyphs" / "mega-evolution.svg").exists():
        return ""
    return img("./assets/glyphs/mega-evolution.svg", "Mega Evolution")


def anchor(text, seen):
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s.strip())
    n = seen[s]
    seen[s] += 1
    return s if n == 0 else f"{s}-{n}"


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
    if not m or any(c not in COST_TYPE for c in m.group(1)):
        return esc(text)
    icons = "".join(type_icon(COST_TYPE[c]) for c in m.group(1))
    return row(icons, esc(m.group(2)), "cost")


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
    head = [mega_sigil(r), esc(r["name"]),
            icon("rarities", RARITY_SLUG.get(r["rarity"]), r["rarity"])]
    art = ["\t\t\t<article>",
           f'\t\t\t\t<h2 id="{a}">' + " ".join(p for p in head if p) + "</h2>"]
    if r["image_file"]:
        art += ["\t\t\t\t<aside>",
                "\t\t\t\t\t" + img(f'./assets/{r["image_file"]}', r["name"]),
                "\t\t\t\t</aside>"]
    art += ["\t\t\t\t<section>", "\t\t\t\t\t<dl>"]
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
          "\t\t\t</aside>"]

# --- assemble ----------------------------------------------------------------
legal = sum(1 for r in rows if r["standard_legal"] == "yes")
subtitle = f"{len(rows)} Pok&eacute;mon, {legal} of them tournament legal."

page = TEMPLATE.read_text(encoding="utf-8")
for token, repl in (("${TITLE}", TITLE),
                    ("${SUBTITLE}", subtitle),
                    ("${NAV}", "\n\t\t\t".join(nav)),
                    ("${ARTICLES}", "\n".join(articles)),
                    ("${NOTES}", "\n".join(notes))):
    page = page.replace(token, repl)

DEST.write_text(page, encoding="utf-8")
print(f"collection.html: {len(rows)} entries, {legal} legal, "
      f"{len(page.splitlines())} lines, {len(page) / 1024:.0f}kb")
