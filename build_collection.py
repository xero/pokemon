#!/usr/bin/env python3
"""Render the Pokemon in cards.csv into collection.md, one HTML table per card.

Pokemon only. Trainers and Energy are dropped, identified by the "Trainer - "
and "Energy - " prefixes normalize_cards.py puts on card_type. Every remaining
row carries an hp and a stage, which is the cross-check that the filter is
cutting on the right seam.

Each entry is a raw HTML table so it renders the same everywhere: a full-width
heading row, then the card image in a th spanning the rest, with one stat row
per CSV column beside it. Sorted by name, then set, then card number.

The heading carries an explicit id because GitHub only mints anchors for
markdown headings, not for HTML ones. GitHub rewrites those ids to
"user-content-<id>" and its own script handles the jump, so the contents
list keeps working.
"""
import csv, html, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "cards.csv"
DEST = ROOT / "collection.md"

# CSV column -> stat label, in the order they should appear. Omits name and
# image_file, which the heading and the image already show, and type_hp_stage,
# which just recombines card_type, hp, and stage. The attack columns are
# handled separately since a card has anywhere from zero to four of them.
LABELS = [
    ("set_name", None),   # set, symbol, and card number on one unlabelled row
    ("rarity", "Rarity"),
    ("card_type", "Type"),
    ("hp", "HP"),
    ("stage", "Stage"),
    ("card_text", "Ability"),
    (None, None),  # attacks slot
    ("weakness", "Weakness"),
    ("resistance", "Resistance"),
    ("retreat_cost", "Retreat"),
    ("standard_legal", "Tournament Play"),
]

# Written for Fox: the badge answers before the words do. Each entry is
# (badge image in assets/, wording).
LEGAL_LABEL = {
    "yes": ("ok", "legal, and good to go!"),
    "no": ("no", "card is too old"),
    "japanese": ("no", "only English cards allowed"),
    "unknown": ("unown", "Unknown, check the letter on the card"),
}

# Anchor for the footnote the unknown state points at.
MARKS_ANCHOR = "checking-the-letter"

# The worked example in that footnote. Two printings of one Pokemon that do
# genuinely different things, one of them the copy in Fox's own deck. Picked by
# (name, set) and resolved to whatever anchor each ends up with, so the links
# survive the collection growing and the sort order shifting underneath them.
EXAMPLE_PAIR = (
    ("Charmander", "SWSH04: Vivid Voltage"),
    ("Charmander", "ME02: Phantasmal Flames"),
)

ATTACKS = ("attack1", "attack2", "attack3", "attack4")

# --- pokesymbols.com graphics -------------------------------------------------
# Most set names slugify straight onto a pokesymbols slug once the "SWSH01:" and
# "SV: " style prefixes are stripped. These are the ones that do not.
SET_SLUG = {
    "Base Set": "base",
    "EX Crystal Guardians": "crystal-guardians",
    "Pokémon GO": "pokemon-go",
    "SV: Scarlet & Violet 151": "151",
    "SWSH01: Sword & Shield Base Set": "sword-and-shield",
    "SWSH: Sword & Shield Promo Cards": "swsh-black-star-promos",
    # pokesymbols has no Trick or Trade entry. All three bundles carry the same
    # Pikachu jack-o'-lantern stamp, so they share one graphic.
    "Trick or Trade BOOster Bundle": "trick-or-trade",
    "Trick or Trade BOOster Bundle 2023": "trick-or-trade",
    "Trick or Trade BOOster Bundle 2024": "trick-or-trade",
    # pokesymbols has no entry for the Japanese starter decks either.
    "MBG: MEGA Starter Set Mega Gengar ex": "megagengar",
    # Battle Academy, the Trick or Trade bundles, and Mega Evolution Energies
    # have no symbol published; they fall through and render without one.
}

# Holo Rare shares the plain black star with Rare and has no symbol of its own.
# Promo is not on the rarities page either; fetch_symbols.py copies the Black
# Star Promo mark in for it, which is what those cards actually print.
RARITY_SLUG = {
    "Common": "common", "Uncommon": "uncommon", "Rare": "rare",
    "Holo Rare": "rare", "Double Rare": "double-rare",
    "Ultra Rare": "ultra-rare", "ACE SPEC Rare": "ace-spec-rare",
    "Promo": "promo",
    # "Art Rare" is what the Japanese line calls what English prints as an
    # Illustration Rare, and the two share a symbol.
    "Art Rare": "illustration-rare",
}


# The glyphs are named for TCG energy types, which is what cards.csv holds, so
# the filename is just the lowercased type. Water, Metal, Fairy, and Dragon are
# listed for completeness even though no card in the collection uses them yet.
TYPES = {"Colorless", "Darkness", "Dragon", "Fairy", "Fighting", "Fire",
         "Grass", "Lightning", "Metal", "Psychic", "Water"}


def type_icon(tcg_type, height=18):
    """The energy glyph for a TCG type, or nothing if it is not a type."""
    if tcg_type not in TYPES:
        return ""
    slug = tcg_type.lower()
    if not (ROOT / "assets" / "types" / f"{slug}.png").exists():
        return ""
    return (f'<img src="./assets/types/{slug}.png" alt="{html.escape(tcg_type)}" '
            f'height="{height}" align="top">')


def typed(v):
    """Prefix a value like "Darkness ×2" or "Fighting -30" with its energy icon."""
    ico = type_icon(v.split(" ")[0])
    return f"{ico} {html.escape(v)}".strip() if ico else html.escape(v)


def set_slug(name):
    if name in SET_SLUG:
        return SET_SLUG[name]
    # Set names arrive prefixed with their code, in a few shapes: "SWSH01: ",
    # "SV: ", "ME03: ", "SM - ", "MBG: ". Strip any of them.
    s = re.sub(r"^[A-Z][A-Z0-9]{1,5}\s*[:\-]\s*", "", name)
    return re.sub(r"[^a-z0-9]+", "-", s.replace("&", "and").lower()).strip("-")


def set_folder(product_line):
    """Japanese sets have their own symbol folder."""
    return "sets-jp" if "japan" in (product_line or "").lower() else "sets"


def mega_sigil(r, height=20):
    """The Mega Evolution sigil, for cards that are one.

    Both signals are checked because they do not always agree across product
    lines: the Japanese line marks the stage "MegaEX" while the name carries
    "Mega", and an English printing may only do one of the two.
    """
    if not (r["stage"].lower().startswith("mega")
            or r["name"].lower().startswith("mega ")):
        return ""
    if not (ROOT / "assets" / "glyphs" / "mega-evolution.svg").exists():
        return ""
    # Referenced as SVG rather than rendered to PNG. The sigil is a four-stop
    # gradient, and ImageMagick silently drops it and hands back a black
    # silhouette. GitHub renders an <img> pointing at a repo SVG fine.
    return ('<img src="./assets/glyphs/mega-evolution.svg" alt="Mega Evolution" '
            f'height="{height}" align="top">')


def icon(folder, slug, height, alt):
    """An inline graphic, or nothing when that slug was never published.

    Several older sets have a logo published but no symbol, so the set icon
    falls back to the wordmark rather than rendering nothing at all.

    Most of these are black line art on transparency and vanish against a dark
    background, so where fetch_symbols.py produced an inverted copy the graphic
    is wrapped in a <picture>. GitHub honours prefers-color-scheme there and
    serves the white version to dark theme.
    """
    if not slug:
        return ""
    for f in ((folder, "set-logos") if folder == "sets" else (folder,)):
        if not (ROOT / "assets" / f / f"{slug}.png").exists():
            continue
        img = (f'<img src="./assets/{f}/{slug}.png" alt="{html.escape(alt)}" '
               f'height="{height}" align="top">')
        if (ROOT / "assets" / f"{f}-dark" / f"{slug}.png").exists():
            return ('<picture>'
                    f'<source media="(prefers-color-scheme: dark)" '
                    f'srcset="./assets/{f}-dark/{slug}.png">{img}</picture>')
        return img
    return ""

NOT_POKEMON = ("Trainer", "Energy")


def anchor(text, seen):
    """Slugify a name, keeping GitHub's -1/-2 suffix for repeats."""
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s.strip())
    n = seen[s]
    seen[s] += 1
    return s if n == 0 else f"{s}-{n}"


def value(key, r):
    """Stat value, HTML-escaped. Card text carries & and < often enough to matter."""
    v = r[key]
    if not v:
        return "-"
    if key == "set_name":
        # Name, symbol, then card number, with no row label. The set name is
        # doing the labelling, and the number only means anything next to it.
        folder = set_folder(r.get("product_line"))
        parts = [f"<b>{html.escape(v)}</b>",
                 icon(folder, set_slug(v), 22, v),
                 html.escape(r["card_number"])]
        return " ".join(p for p in parts if p)
    if key == "rarity":
        return f'{icon("rarities", RARITY_SLUG.get(v), 16, v)} {html.escape(v)}'.strip()
    if key == "source_url":
        label = re.sub(r"^.*?/pokemon(?:-japan)?/", "", v)
        return f'<a href="{html.escape(v)}">{html.escape(label)}</a>'
    if key in ("card_type", "weakness", "resistance"):
        return typed(v)
    if key == "retreat_cost":
        # Retreat is paid in any energy, so it prints as that many Colorless
        # symbols. Showing them beats a bare digit for someone learning.
        n = int(v) if v.isdigit() else 0
        ico = type_icon("Colorless", 16)
        return f"{ico * n} {html.escape(v)}".strip() if ico and n else html.escape(v)
    if key == "standard_legal":
        badge, text = LEGAL_LABEL.get(v, ("", v))
        img = ""
        if badge and (ROOT / "assets" / f"{badge}.png").exists():
            img = (f'<img src="./assets/{badge}.png" alt="{badge.upper()}" '
                   'height="22" align="top"> ')
        out = img + html.escape(text)
        if v == "unknown":
            out += f' <a href="#{MARKS_ANCHOR}">*</a>'
        return out
    if key == "card_text":
        # normalize_cards.py prefixes the description with "Ability: ", which
        # would read twice over once the row label already says Ability.
        v = re.sub(r"^Ability:\s*", "", v)
    return html.escape(v)


all_rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
rows = [r for r in all_rows if not r["card_type"].startswith(NOT_POKEMON)]
rows.sort(key=lambda r: (r["name"].lower(), r["set_name"], r["card_number"]))

if any(not r["hp"] or not r["stage"] for r in rows):
    raise SystemExit("a kept row has no hp or stage; the Pokemon filter is wrong")

def stats(r):
    """(label, html) pairs for one card, skipping attacks it does not have.

    A label of None means the row carries no "Label:" prefix and the html
    stands on its own.
    """
    out = []
    for key, label in LABELS:
        if key is None:
            hits = [r[k] for k in ATTACKS if r[k]]
            out += [("Attack", html.escape(a)) for a in hits]
        else:
            out.append((label, value(key, r)))
    return out


seen = Counter()
entries = [(r, anchor(r["name"], seen)) for r in rows]

# An HTML h1 rather than a markdown one, so the Poké Ball can sit inside it.
# It is full colour and needs no dark-theme variant.
out = ['<h1><img src="./assets/pokeball.png" alt="" height="40" align="top"> '
       "Pokémon Caught!</h1>\n"]

# The blank lines around the list are load-bearing. Without them GitHub treats
# the whole <details> block as raw HTML and the markdown links never render.
toc = ["<details>", "<summary><h3>Pokédex</h3></summary>", ""]
last_letter = None
for r, a in entries:
    letter = r["name"][0].upper()
    if letter != last_letter:
        toc.append(f"- **{letter}**")
        last_letter = letter
    toc.append(f"  - [{r['name']}](#{a}) _{r['set_name']}_")
toc += ["", "</details>"]
out += ["\n".join(toc), ""]

for r, a in entries:
    cells = stats(r)
    # The image th spans its own row plus every stat row that follows it, and
    # that count moves with how many attacks the card has.
    span = len(cells) + 1
    out.append("<table>")
    rare = icon("rarities", RARITY_SLUG.get(r["rarity"]), 18, r["rarity"])
    mega = mega_sigil(r)
    out.append(f'  <tr><td colspan="2"><h3 id="{a}">'
               f'{mega + " " if mega else ""}{html.escape(r["name"])}'
               f'{" " + rare if rare else ""}</h3></td></tr>')
    if r["image_file"]:
        out.append("  <tr>")
        out.append(f'    <th rowspan="{span}" width="400">'
                   f'<img src="./assets/{r["image_file"]}" width="350"></th>')
        out.append("  </tr>")
    for label, v in cells:
        cell = f"<b>{label}</b>: {v}" if label else v
        out.append(f"  <tr><td>{cell}</td></tr>")
    out.append("</table>")
    out.append("")

# Footnote for the unknown badge. An HTML heading rather than a markdown one so
# the id is ours to pick and the link from every unknown row keeps working.
out += [
    f'<h2 id="{MARKS_ANCHOR}">* Checking the letter</h2>',
    "",
    "> [!IMPORTANT]",
    "> Every modern card has a tiny letter printed in the bottom corner, next to"
    " the card number. That letter is the only thing that decides whether a card"
    " is too old to play. The set it came from does not decide it, and neither"
    " does how new the card looks.",
    ">",
    "> Right now three letters are legal: **H**, **I**, and **J**.",
    ">",
    "> **G and anything older rotated out** on 10 April 2026. A card with no"
    " letter at all is older still, so it is out too.",
    "",
]

out += [
    "> [!WARNING]",
    "> Two cards can share a name and still be completely different cards. One"
    " can have an Ability the other does not. The attacks can cost different"
    " Energy and do different damage. The name on the card is not the card.",
]

# The worked example is a bonus. If either printing leaves the collection the
# warning above still says everything it needs to.
by_card = {(r["name"], r["set_name"]): (r, a) for r, a in entries}
pair = [by_card.get(k) for k in EXAMPLE_PAIR]
if all(pair):
    (r1, a1), (r2, a2) = pair

    def sketch(r):
        bits = ["an **Ability**" if r["card_text"] else "no Ability"]
        atk = [r[k] for k in ATTACKS if r[k]]
        if atk:
            bits.append(f"{len(atk)} attack" + ("s" if len(atk) > 1 else ""))
        return " and ".join(bits)

    out += [
        ">",
        f"> Comparing [{r1['name']}, {r1['set_name']}](#{a1}) and"
        f" [{r2['name']}, {r2['set_name']}](#{a2}) side by side:",
        ">",
        f"> - The {r1['set_name']} one has {sketch(r1)}.",
        f"> - The {r2['set_name']} one has {sketch(r2)}.",
        ">",
        "> One of those is in your deck and one is legal today, and they are"
        " still not the same card.",
    ]

out += [">", "> Read the one in your hand every time.", ""]

text = "\n".join(out)
DEST.write_text(text, encoding="utf-8")
print(f"collection.md: {len(rows)} entries, "
      f"{sum(r['category'] == 'deck' for r in rows)} in decks, "
      f"{len(text.splitlines())} lines")
