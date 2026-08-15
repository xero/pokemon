#!/usr/bin/env python3
"""Snapshot every Standard-legal card to legal-cards-<epoch>.json.

Nothing in the build reads this. It exists so a session can answer "what is
legal that does X" by grepping a local file, instead of guessing from memory or
paging a flaky API mid-conversation. cards.csv only knows the ~200 cards we own,
which is the wrong pool for that question.

The filename carries the fetch time because the answer expires: rotation moves
the legal marks every April, and sets are added between rotations. An old
snapshot is still useful (diff two of them to see what a rotation took), so this
writes a new file rather than overwriting the last one.

Marks are the whole point, so they are the query rather than a filter applied
afterwards -- see fetch_regulation.py for why the mark cannot be inferred from
the set. LEGAL_MARKS is the one line to edit after a rotation.

The upstream API returns bare 502s in bursts, badly enough that a Pokemon page
can need a dozen attempts, so every request retries. Runtime is a few minutes.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
API = "https://api.pokemontcg.io/v2/cards"
ATTEMPTS = 12

# Standard as of the 2026 rotation. Verified against regulation-marks.json,
# which is built from the same upstream and is what cards.csv actually uses.
LEGAL_MARKS = ["H", "I", "J"]

# The fields that answer "what does this card do". The full record carries
# prices, market ids, and a dozen image urls, which would quadruple the file
# and go stale immediately.
FIELDS = ("id,name,supertype,subtypes,number,set,regulationMark,rules,"
          "abilities,attacks,types,hp")


def get(query, page):
    for i in range(ATTEMPTS):
        out = subprocess.run(
            ["curl", "-s", "-G", API,
             "--data-urlencode", f"q={query}",
             "--data-urlencode", f"select={FIELDS}",
             "--data-urlencode", f"page={page}",
             "--data-urlencode", "pageSize=250",
             "--max-time", "90"],
            capture_output=True, text=True).stdout
        try:
            d = json.loads(out)
            if "data" in d:
                return d["data"]
        except json.JSONDecodeError:
            pass
        time.sleep(2)
    sys.exit(f"gave up on {query!r} page {page} after {ATTEMPTS} attempts")


def pull(query):
    """Page until short. The API has no reliable total to trust instead."""
    cards, page = [], 1
    while True:
        batch = get(query, page)
        cards += batch
        if len(batch) < 250:
            return cards
        page += 1


# The query spells it "Pokemon" and the returned records spell it "Pokémon",
# and the field is missing outright on some Trainers. Neither is worth working
# around per card: what we asked for is what came back, so stamp it ourselves.
cards = []
for supertype in ("Trainer", "Pokemon", "Energy"):
    for mark in LEGAL_MARKS:
        batch = pull(f"regulationMark:{mark} supertype:{supertype}")
        for c in batch:
            c["supertype"] = supertype
        print(f"{supertype:8} {mark}  {len(batch):5}", file=sys.stderr)
        cards += batch

cards.sort(key=lambda c: (c["supertype"], c["set"]["id"], c["name"],
                          c["number"]))
stamp = int(time.time())
dest = ROOT / f"legal-cards-{stamp}.json"
dest.write_text(json.dumps({
    "fetched_epoch": stamp,
    "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stamp)),
    "legal_marks": LEGAL_MARKS,
    "source": API,
    "counts": {s: sum(1 for c in cards if c["supertype"] == s)
               for s in ("Trainer", "Pokemon", "Energy")},
    "cards": cards,
}, indent=0, sort_keys=True))
print(f"{len(cards)} cards -> {dest.name}")
