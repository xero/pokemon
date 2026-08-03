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
    ("set_name", "Set"),
    ("card_number", "Number"),
    ("card_type", "Type"),
    ("hp", "HP"),
    ("stage", "Stage"),
    ("card_text", "Ability"),
    (None, None),  # attacks slot
    ("weakness", "Weakness"),
    ("resistance", "Resistance"),
    ("retreat_cost", "Retreat"),
    ("category", "Category"),
    ("source_url", "Source"),
]

ATTACKS = ("attack1", "attack2", "attack3", "attack4")

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
    if key == "source_url":
        return f'<a href="{html.escape(v)}">{html.escape(v.rsplit("/pokemon/", 1)[-1])}</a>'
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
    """(label, html) pairs for one card, skipping attacks it does not have."""
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

out = ["# Pokémon Caught!\n"]

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
    out.append(f'  <tr><td colspan="2"><h3 id="{a}">{html.escape(r["name"])}</h3></td></tr>')
    if r["image_file"]:
        out.append("  <tr>")
        out.append(f'    <th rowspan="{span}" width="400">'
                   f'<img src="./assets/{r["image_file"]}" width="350"></th>')
        out.append("  </tr>")
    for label, v in cells:
        out.append(f"  <tr><td><b>{label}</b>: {v}</td></tr>")
    out.append("</table>")
    out.append("")

DEST.write_text("\n".join(out), encoding="utf-8")
print(f"collection.md: {len(rows)} entries, "
      f"{sum(r['category'] == 'deck' for r in rows)} in decks, "
      f"{len(out)} lines")
