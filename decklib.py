"""The page registry, and the deck lists written inside the markdown.

decks.toml is the one place a page is registered. This module is its only
reader, so the deck builder, the front page, and the pull list agree on what is
published, whose deck it is, and in what order it is listed.
"""
import re
import tomllib
from pathlib import Path

from pokelib import find_card

ROOT = Path(__file__).parent
REGISTRY = ROOT / "decks.toml"

PLAYERS = ("xero", "fox")
SHELVES = ("league", "other", "opponent")


def load():
    """(library, decks) from decks.toml, checked, with the defaults filled in.

    Every entry comes back with page, sprites, mascot, blurb, flavor, and
    draft set, so no reader has to know which keys are optional. A problem
    stops the build rather than printing a warning nobody reads, because a
    registry typo otherwise publishes a page nobody links or links a page
    nobody built.
    """
    data = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    library, decks = data.get("library", []), data.get("deck", [])
    problems = []

    for e in library + decks:
        src = e.get("source", "")
        if src and not (ROOT / src).exists():
            problems.append(f"{src}: no such file")
        if not src and not e.get("page"):
            problems.append(f"an entry has neither source nor page: {e}")
        e["page"] = e.get("page") or (src[:-3] + ".html" if src else "")
        e.setdefault("sprites", [])
        e.setdefault("mascot", e["sprites"])
        e.setdefault("flavor", {})
        e["draft"] = bool(e.get("draft", False))
        # the line breaks in the file are for reading it, not for the page
        e["blurb"] = " ".join(e.get("blurb", "").split())

    for d in decks:
        name = d.get("source", "?")
        if not d.get("source", "").endswith(".md"):
            problems.append(f"{name}: a deck needs a markdown source")
        if d.get("player") not in PLAYERS:
            problems.append(f"{name}: player must be one of {PLAYERS}")
        if d.get("shelf") not in SHELVES:
            problems.append(f"{name}: shelf must be one of {SHELVES}")
        if d.get("shelf") == "other" and not d.get("group"):
            problems.append(f"{name}: an other-shelf deck needs a group")

    if problems:
        raise SystemExit("decks.toml:\n  " + "\n  ".join(problems))
    return library, decks


def published(entries):
    """The entries that make it onto the site."""
    return [e for e in entries if not e["draft"]]


def qty_rows(text):
    """[(copies, name, set words, number)] from every table led by a Qty column.

    The same reading the deck builder gives the deck list: the Card, Set, and
    Number columns, a number printed inside the Set cell when there is no
    Number column, and a row with no set treated as a flex slot rather than a
    card. A table led by anything else, such as | Out | In |, is skipped, which
    is how a page shows a variant without it counting.
    """
    out, head = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            head = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells[0].strip("*").lower() == "qty":
            head = [c.strip("*").lower() for c in cells]
            continue
        if head is None or set("".join(cells)) <= set("-: "):
            continue
        if not cells[0].strip("*").isdigit():
            continue

        def col(want):
            j = head.index(want) if want in head else -1
            return cells[j] if 0 <= j < len(cells) else ""

        name = re.sub(r"\*+|\[.*?\]", "", col("card")).strip()
        hint, num = col("set"), col("number").strip("*")
        m = re.search(r"(\d{2,3})\s*$", hint)
        if not num and m:
            num, hint = m.group(1), hint[:m.start()]
        hint = hint.strip()
        if not name or set(hint) <= set("—- "):
            continue
        out.append((int(cells[0].strip("*")), name, hint, num))
    return out


def card_key(r):
    return (r["name"], r["set_name"], r["card_number"])


def deck_cards(source):
    """{card key: copies} for one deck, resolved against cards.csv.

    A card listed twice takes the later count, the same as the count badges on
    the deck page, so the page and the pull list cannot disagree about it. A row
    that resolves to nothing is left out; the deck builder already names those.
    """
    out = {}
    for copies, name, hint, num in qty_rows((ROOT / source).read_text(encoding="utf-8")):
        r = find_card(name, hint, num)
        if r:
            out[card_key(r)] = copies
    return out
