#!/usr/bin/env python3
"""Add cards to product-ids.tsv by searching TCGplayer for them.

    python3 add_cards.py wanted.tsv [--dry-run]

The seed needs a productId, and that is not derivable from a card name, so each
wanted card is looked up through the same marketplace search the normaliser
uses. A card number in the wanted list pins the answer: "Umbreon ex" matches
both the $2 Double Rare 060/131 and the Special Illustration Rare 161/131, and
picking the wrong one is an expensive mistake.

The input is tab separated, blank lines and # comments ignored:

    query<TAB>number<TAB>quantity<TAB>note

    Umbreon ex Prismatic Evolutions   060/131   0   eevee-standard wants 2
    Yanmega Vivid Voltage             007/185   2   charizard theme deck

number may be blank when a name is unambiguous. quantity is what goes in the
seed, so 0 for a wishlist card. Anything already in the seed is skipped, so the
file is safe to re-run after adding a line to it.
"""
import json, re, subprocess, sys, time, unicodedata, urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
SEED = ROOT / "product-ids.tsv"
API = "https://mp-search-api.tcgplayer.com/v1/search/request"


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace("&", "and").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-").lower()


def search(q, line):
    url = f"{API}?q={urllib.parse.quote(q)}&isList=false"
    body = json.dumps({
        "algorithm": "sales_synonym_v2", "from": 0, "size": 20,
        "filters": {"term": {"productLineName": [line]}, "range": {}, "match": {}},
        "listingSearch": {"context": {"cart": {}},
                          "filters": {"term": {}, "range": {},
                                      "exclude": {"channelExclusion": 0}}},
        "context": {"cart": {}, "shippingCountry": "US"}, "sort": {}})
    out = subprocess.run(["curl", "-s", url, "-H", "Content-Type: application/json",
                          "-H", "User-Agent: Mozilla/5.0", "-d", body, "--max-time", "40"],
                         capture_output=True, text=True).stdout
    try:
        return json.loads(out)["results"][0]["results"]
    except Exception:
        return []


def pick(hits, number, query):
    """The hit matching both the printed number and the set the query names.

    Number alone is not enough. The Gengar and Diancie starter sets are both
    21 cards, so "011/021" exists in each, and matching on number alone put
    the Gengar deck's Ultra Ball in the Diancie set.
    """
    words = {w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2}
    if number:
        want = number.split("/")[0].lstrip("0")
        hits = [h for h in hits
                if str((h.get("customAttributes") or {}).get("number") or ""
                       ).split("/")[0].lstrip("0") == want]
    if not hits:
        return None
    def score(h):
        setw = {w for w in re.findall(r"[a-z]+", str(h.get("setName") or "").lower())}
        return len(words & setw)
    top = max(map(score, hits))
    hits = [h for h in hits if score(h) == top]
    if len(hits) == 1:
        return hits[0]
    # 151's Gengar is one number across three printings: the plain card and two
    # pattern variants. A parenthetical means a variant, so the base print wins.
    plain = [h for h in hits if "(" not in h["productName"]]
    return plain[0] if len(plain) == 1 else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    wanted = Path(args[0]) if args else ROOT / "wanted-cards.tsv"

    seed_lines = [l for l in SEED.read_text(encoding="utf-8").splitlines() if l.strip()]
    have = {int(float(l.split("\t")[0])) for l in seed_lines}

    added, missed, ambiguous = [], [], []
    for line in wanted.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = (line.split("\t") + [""] * 4)[:4]
        query, number, qty, note = (x.strip() for x in f)
        line_name = "pokemon-japan" if "japan" in note.lower() else "pokemon"
        hits = search(query, line_name)
        best = pick(hits, number, query)
        if best is None:
            (ambiguous if hits else missed).append(
                (query, number, [f'{h["productName"]} ({h.get("setName")})'
                                 for h in hits[:4]]))
            continue
        pid = int(float(best["productId"]))
        url = (f'https://store.tcgplayer.com/{slug(best["productLineUrlName"])}/'
               f'{slug(best["setUrlName"])}/{slug(best["productUrlName"])}')
        if pid in have:
            print(f"  have  {best['productName']}")
            continue
        have.add(pid)
        added.append(f"{pid}\t{url}\t{qty or 0}")
        print(f"  add   {qty or 0:>2}x {best['productName']:<38} {best.get('setName')}")
        time.sleep(0.4)

    for label, rows in (("no match", missed), ("ambiguous, pin the number", ambiguous)):
        if rows:
            print(f"\n  {len(rows)} {label}:", file=sys.stderr)
            for q, n, opts in rows:
                print(f"    {q} [{n or 'no number'}]", file=sys.stderr)
                for o in opts:
                    print(f"        {o}", file=sys.stderr)

    print(f"\n  {len(added)} new rows, {len(missed) + len(ambiguous)} unresolved")
    if added and not dry:
        SEED.write_text("\n".join(seed_lines + added) + "\n", encoding="utf-8")


main()
