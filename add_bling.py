#!/usr/bin/env python3
"""Seed the prints a deck's Bling Deck names into bling-ids.tsv.

    python3 add_bling.py                  # every deck with a Bling Deck
    python3 add_bling.py overgrowth.md    # just this one
    python3 add_bling.py --dry-run        # say what it would add

A Bling Deck is a deck's same sixty in prints nobody here owns: illustration
rares, full arts, gold secret rares. The deck's markdown lists them in a table
led by Copies, under its Deck List, by the set code and number Limitless's deck
builder uses (TWM 211). The deck page deals those prints in place of the
regular ones when the $$$ is pressed, and each card section shows the first
bling print's own set, rarity, and scan. So every print goes through the same
TCGplayer lookup add_cards.py uses, into a seed of its own.

Its own seed, because product-ids.tsv is ownership: a card in it is in the
binders or on the pull list, and these are neither. Seeded there, the bling
prints would land on the collection page as ours or on the pull list as forty
things to go buy. normalize_cards.py turns this seed into bling.csv, which
nothing but the deck pages reads.

The lookup searches TCGplayer by card name and keeps the hit with the table's
set code and number. TCGplayer's set codes are Limitless's for every set from
Scarlet & Violet on; the older ones TCGplayer numbers its own way, and ALIASES
maps those. A name too common for one search to reach the print, like Switch,
and a secret Basic Energy, which TCGplayer calls "Grass Energy (Secret)", are
searched for again inside their own set. Where one number carries a variant
too, a Staff stamp or a Poke Ball pattern, the plain print wins, unless the
Card cell names the variant in parens: "Bug Catching Set (Poke Ball Pattern)".

A print it cannot pin is reported with what the search saw at that number, so
a new old set is one line in ALIASES. After this, run normalize_cards.py and
then build.py.
"""
import argparse, json, re, sys, time
from pathlib import Path

import add_cards
from decklib import bling_rows, load, published

ROOT = Path(__file__).parent
SEED = ROOT / "bling-ids.tsv"
RAW = ROOT / "raw-cards.json"

# Limitless set code -> TCGplayer setCode, for the sets before Scarlet &
# Violet, which TCGplayer numbers rather than names. Only codes seen on
# TCGplayer are here, and its numbering is irregular (SM8 and SM9, but SM02
# and SM10), so a missing one is looked up, never guessed.
ALIASES = {
    "SUM": "SM01", "GRI": "SM02", "BUS": "SM03", "CIN": "SM04",
    "FLI": "SM06", "LOT": "SM8", "TEU": "SM9", "UNB": "SM10",
    "SSH": "SWSH01", "RCL": "SWSH02", "DAA": "SWSH03", "VIV": "SWSH04",
    "BST": "SWSH05", "CRE": "SWSH06", "EVS": "SWSH07", "FST": "SWSH08",
    "BRS": "SWSH09", "LOR": "SWSH11",
}

HEADER = """\
# The Bling Deck prints: TCGplayer product id, store URL, and the set code and
# number the deck's Copies table names the print by.
#
# add_bling.py writes this file from the Copies tables in the deck markdown.
# normalize_cards.py turns it into bling.csv, cards.csv's columns with the set
# code in place of owned, and fetches the scans. Nothing here is owned or
# wanted, which is why it is not in product-ids.tsv: these never reach the
# collection page or the pull list.
"""


def number(hit):
    n = str((hit.get("customAttributes") or {}).get("number") or "")
    return n.split("/")[0].lstrip("0")


def plain(hits, variant=""):
    """The one hit that is the print asked for, if exactly one is: the one
    whose name carries the variant the table asked for, or with none asked
    for, the one that is not a variant at all."""
    if variant:
        hits = [h for h in hits if variant.lower() in h["productName"].lower()]
        return hits[0] if len(hits) == 1 else None
    if len(hits) == 1:
        return hits[0]
    bare = [h for h in hits if not re.search(r"[\[(]", h["productName"])]
    return bare[0] if len(bare) == 1 else None


def set_url_names():
    """TCGplayer setCode -> the setUrlName its search filters on, from the
    products already cached. A set we hold nothing from is learned from the
    name search instead."""
    if not RAW.exists():
        return {}
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    return {p["setCode"]: p["setUrlName"] for p in raw.values()
            if p.get("setCode") and p.get("setUrlName")}


def resolve(name, code, num, urls):
    """(hit, why it failed). Exactly one of the two is set.

    A parenthetical on the name picks a variant that shares the number, so
    "Bug Catching Set (Poke Ball Pattern)" is the pattern print and a bare
    "Bug Catching Set" the plain one. The deck page matches the row to its
    card section by the name without it.
    """
    m = re.match(r"(.*?)\s*\(([^()]*)\)\s*$", name)
    name, variant = (m.group(1), m.group(2)) if m else (name, "")
    want = ALIASES.get(code, code)
    hits = add_cards.api(add_cards.body({"productLineName": ["pokemon"]},
                                        size=50), name)
    at = [h for h in hits if number(h) == num]
    exact = [h for h in at if h.get("setCode") == want]
    if exact:
        hit = plain(exact, variant)
        return (hit, "") if hit else (None, "more than one print at that "
                "number; name the one you mean in parens: "
                + "; ".join(h["productName"] for h in exact))
    # not reached by name: search inside the set, under the name TCGplayer
    # would give it ("Grass Energy (Secret)", not "Basic Grass Energy")
    url = urls.get(want) or next(
        (h["setUrlName"] for h in hits if h.get("setCode") == want), "")
    if url:
        query = re.sub(r"^Basic\s+", "", name)
        inside = add_cards.api(add_cards.body(
            {"productLineName": ["pokemon"], "setName": [url]}, size=50), query)
        exact = [h for h in inside if number(h) == num]
        hit = plain(exact, variant)
        if hit:
            return hit, ""
    seen = "; ".join(f'{h.get("setCode")} {h["productName"]}' for h in at[:4])
    return None, (f"no {want} {num} found. same number elsewhere: {seen}"
                  if seen else f"no {want} {num} found, and no set to search")


def read_seed():
    """([raw line, ...], {(code, number), ...}), notes kept as they are."""
    if not SEED.exists():
        return HEADER.rstrip("\n").splitlines(), set()
    lines = [l for l in SEED.read_text(encoding="utf-8").splitlines() if l.strip()]
    keys = set()
    for l in lines:
        if l.startswith("#"):
            continue
        parts = l.split("\t")
        if len(parts) > 2:
            code, _, num = parts[2].partition(" ")
            keys.add((code, num))
    return lines, keys


def main():
    p = argparse.ArgumentParser(
        description="Seed the prints a deck's Bling Deck names into bling-ids.tsv.")
    p.add_argument("decks", nargs="*", help="deck markdown files; default every deck")
    p.add_argument("--dry-run", action="store_true",
                   help="say what would be added, write nothing")
    args = p.parse_args()

    if args.decks:
        sources = [Path(d) for d in args.decks]
    else:
        _, decks = load()
        sources = [ROOT / e["source"] for e in published(decks)]

    lines, have = read_seed()
    urls = set_url_names()
    added, problems = 0, []
    for src in sources:
        rows = bling_rows(src.read_text(encoding="utf-8"))
        for _, name, code, num in rows:
            if (code, num) in have:
                continue
            hit, why = resolve(name, code, num, urls)
            time.sleep(0.4)
            if not hit:
                problems.append((src.name, f"{name} {code} {num}", why))
                continue
            have.add((code, num))
            lines.append(f'{int(float(hit["productId"]))}\t'
                         f'{add_cards.store_url(hit)}\t{code} {num}')
            added += 1
            print(f"  add   {code} {num:>3}  {hit['productName']} "
                  f"({hit.get('setName')}, {hit.get('rarityName')})")

    for deck, card, why in problems:
        print(f"  ??    {deck}: {card}\n          {why}", file=sys.stderr)
    print(f"\n  {added} added, {len(problems)} unresolved")
    if added and not args.dry_run:
        SEED.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("  wrote bling-ids.tsv. next: normalize_cards.py, then build.py")
    elif args.dry_run:
        print("  --dry-run, nothing written")
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
