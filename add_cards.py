#!/usr/bin/env python3
"""Add cards to product-ids.tsv, by name, by URL, or a fileful at a time.

    python3 add_cards.py "Umbreon ex Prismatic Evolutions" -n 060/131 -q 2
    python3 add_cards.py https://www.tcgplayer.com/product/94663/... -q 0
    python3 add_cards.py --file wanted-cards.tsv
    python3 add_cards.py                       # the same, wanted-cards.tsv

The seed needs a productId, and that is not derivable from a card name, so a
name goes through the same marketplace search the normaliser uses. A URL skips
the search entirely: TCGplayer puts the productId in the path, and looking that
id up straight gives the canonical store URL back with no guessing.

Pin the printing with --number whenever a name has more than one. "Umbreon ex"
matches both the $2 Double Rare 060/131 and the Special Illustration Rare
161/131, and picking the wrong one is an expensive mistake.

--quantity is what goes in the seed: how many you own, or 0 for a card a deck
plan wants but you have not bought. A 0 still gets a full card page in the deck
plans, which is the whole reason the column exists.

The batch file is tab separated, blank lines and # comments ignored:

    query<TAB>number<TAB>quantity<TAB>note

    Umbreon ex Prismatic Evolutions   060/131   0   eevee-standard wants 2
    Yanmega Vivid Voltage             007/185   2   charizard theme deck

A card already in the seed is skipped, so the file is safe to re-run after
adding a line to it. Naming one card explicitly instead updates its quantity,
since "add this card, I own 2" is a statement about now, not a duplicate.

After this, run normalize_cards.py to pull the card data, then build.py.
"""
import argparse, json, re, subprocess, sys, time, unicodedata, urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
SEED = ROOT / "product-ids.tsv"
WANTED = ROOT / "wanted-cards.tsv"
API = "https://mp-search-api.tcgplayer.com/v1/search/request"

# TCGplayer product URLs carry the id in the path, whatever the slug says:
# https://www.tcgplayer.com/product/94663/pokemon-xy-phantom-forces-gengar...
PRODUCT_URL = re.compile(r"tcgplayer\.com/product/(\d+)", re.I)


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace("&", "and").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-").lower()


def api(payload, query=""):
    """One marketplace search. The query goes in the URL, the rest in the body."""
    url = f"{API}?q={urllib.parse.quote(query)}&isList=false"
    out = subprocess.run(
        ["curl", "-s", url, "-H", "Content-Type: application/json",
         "-H", "User-Agent: Mozilla/5.0", "-d", json.dumps(payload),
         "--max-time", "40"], capture_output=True, text=True).stdout
    try:
        return json.loads(out)["results"][0]["results"]
    except Exception:
        return []


def body(term, size=20):
    return {"algorithm": "sales_synonym_v2", "from": 0, "size": size,
            "filters": {"term": term, "range": {}, "match": {}},
            "listingSearch": {"context": {"cart": {}},
                              "filters": {"term": {}, "range": {},
                                          "exclude": {"channelExclusion": 0}}},
            "context": {"cart": {}, "shippingCountry": "US"}, "sort": {}}


def search(q, line):
    return api(body({"productLineName": [line]}), q)


def by_id(pid):
    """The one product with this id, straight from the search index.

    Both product lines are asked at once. A URL does not say which line it is
    on, and the id is unique across both anyway.
    """
    hits = api(body({"productLineName": ["pokemon", "pokemon-japan"],
                     "productId": [int(pid)]}, size=1))
    return hits[0] if hits else None


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
        return len(words & set(re.findall(r"[a-z]+", str(h.get("setName") or "").lower())))

    top = max(map(score, hits))
    hits = [h for h in hits if score(h) == top]
    if len(hits) == 1:
        return hits[0]
    # 151's Gengar is one number across three printings: the plain card and two
    # pattern variants. A parenthetical means a variant, so the base print wins.
    plain = [h for h in hits if "(" not in h["productName"]]
    return plain[0] if len(plain) == 1 else None


def store_url(hit):
    return (f'https://store.tcgplayer.com/{slug(hit["productLineUrlName"])}/'
            f'{slug(hit["setUrlName"])}/{slug(hit["productUrlName"])}')


def resolve(query, number, note):
    """(hit, why it failed). Exactly one of the two is set."""
    m = PRODUCT_URL.search(query)
    if m:
        hit = by_id(m.group(1))
        return (hit, "") if hit else (None, f"no product with id {m.group(1)}")
    if query.startswith(("http://", "https://")):
        return None, "a URL, but not a tcgplayer.com/product/<id>/... one"
    line = "pokemon-japan" if "japan" in note.lower() else "pokemon"
    hits = search(query, line)
    if not hits:
        return None, "nothing matched"
    best = pick(hits, number, query)
    if best:
        return best, ""
    options = ", ".join(f'{h["productName"]} ({h.get("setName")})' for h in hits[:4])
    return None, f"ambiguous, pin it with --number. Saw: {options}"


def read_seed():
    """([raw line, ...], {productId: index into that list})."""
    lines = [l for l in SEED.read_text(encoding="utf-8").splitlines() if l.strip()]
    return lines, {int(float(l.split("\t")[0])): i for i, l in enumerate(lines)}


def wanted_rows(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = (line.split("\t") + [""] * 4)[:4]
        yield tuple(x.strip() for x in f)


def main():
    p = argparse.ArgumentParser(
        description="Add a card to product-ids.tsv by name or TCGplayer URL.")
    p.add_argument("card", nargs="?", default="",
                   help="card name and set, or a tcgplayer.com/product/... URL")
    p.add_argument("-n", "--number", default="",
                   help="printed number, e.g. 060/131. Pins the printing.")
    p.add_argument("-q", "--quantity", default="0",
                   help="how many you own. 0 for a wishlist card.")
    p.add_argument("--note", default="", help="why it is on the list")
    p.add_argument("-f", "--file", help="a batch of cards, tab separated")
    p.add_argument("--dry-run", action="store_true",
                   help="say what would change, write nothing")
    args = p.parse_args()

    if args.card:
        jobs = [(args.card, args.number, args.quantity, args.note)]
    else:
        path = Path(args.file) if args.file else WANTED
        if not path.exists():
            raise SystemExit(f"no such file: {path}")
        jobs = list(wanted_rows(path))
    # naming one card is a statement about it; a batch file is a record of what
    # was once wanted, so re-running it must not rewrite quantities since.
    single = bool(args.card)

    lines, index = read_seed()
    added = changed = 0
    problems = []

    for query, number, qty, note in jobs:
        hit, why = resolve(query, number, note)
        if not hit:
            problems.append((query, why))
            continue
        pid = int(float(hit["productId"]))
        qty = qty or "0"
        label = f'{hit["productName"]} ({hit.get("setName")})'

        if pid in index:
            row = lines[index[pid]].split("\t")
            was = row[2] if len(row) > 2 else "0"
            if single and was != qty:
                lines[index[pid]] = f"{row[0]}\t{row[1]}\t{qty}"
                changed += 1
                print(f"  set   {was} -> {qty:<3} {label}")
            else:
                print(f"  have  {' ' * 8}{label}")
            continue

        index[pid] = len(lines)
        lines.append(f"{pid}\t{store_url(hit)}\t{qty}")
        added += 1
        print(f"  add   {qty:>2}x      {label}")
        if not single:
            time.sleep(0.4)

    for query, why in problems:
        print(f"  ??    {query}\n          {why}", file=sys.stderr)

    print(f"\n  {added} added, {changed} updated, {len(problems)} unresolved")
    if problems and not added and not changed:
        raise SystemExit(1)
    if (added or changed) and not args.dry_run:
        SEED.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("  wrote product-ids.tsv. next: normalize_cards.py, then build.py")
    elif args.dry_run:
        print("  --dry-run, nothing written")


# Guarded because search(), resolve(), and wanted_rows() are the obvious things
# to reuse from another script or a REPL, and without this an `import add_cards`
# silently runs the whole batch and rewrites product-ids.tsv. Not hypothetical;
# it has happened. Nothing here imports the module, so running it as a script is
# unaffected.
if __name__ == "__main__":
    main()
