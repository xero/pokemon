#!/usr/bin/env python3
"""Add a card to product-ids.tsv, or flip whether we own it.

    python3 add_cards.py "Umbreon ex Prismatic Evolutions" -n 060/131
    python3 add_cards.py "Umbreon ex Prismatic Evolutions" -n 060/131 --need
    python3 add_cards.py https://www.tcgplayer.com/product/94663/... --have
    python3 add_cards.py --japanese "Ultra Ball MEGA Starter Set Mega Gengar ex" -n 011/021
    python3 add_cards.py --file cards.tsv

The seed needs a productId, and that is not derivable from a card name, so a
name goes through the same marketplace search the normaliser uses. A URL skips
the search entirely: TCGplayer puts the productId in the path, and looking that
id up straight gives the canonical store URL back with no guessing.

Pin the printing with --number whenever a name has more than one. "Umbreon ex"
matches both the $2 Double Rare 060/131 and the Special Illustration Rare
161/131, and picking the wrong one is an expensive mistake.

Every card is owned unless someone says otherwise. --need adds the card as not
owned, or flips an existing one, and that is the whole of how a card reaches
the pull list. --have flips it back once it is in the binder. Naming a card
that is already in the seed with neither flag changes nothing.

The search runs against one product line at a time; --japanese switches it to
the Japanese one. A URL needs no hint, since an id is unique across both.

A batch file is tab separated, blank lines and # comments ignored, one card a
line. The third column is optional and takes need or have, the same as the
flags:

    query<TAB>number<TAB>need

    Umbreon ex Prismatic Evolutions   060/131   need
    Yanmega Vivid Voltage             007/185

After this, run normalize_cards.py to pull the card data, then build.py.
"""
import argparse, json, re, subprocess, sys, time, unicodedata, urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
SEED = ROOT / "product-ids.tsv"
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


def resolve(query, number, japanese=False):
    """(hit, why it failed). Exactly one of the two is set."""
    m = PRODUCT_URL.search(query)
    if m:
        hit = by_id(m.group(1))
        return (hit, "") if hit else (None, f"no product with id {m.group(1)}")
    if query.startswith(("http://", "https://")):
        return None, "a URL, but not a tcgplayer.com/product/<id>/... one"
    line = "pokemon-japan" if japanese else "pokemon"
    hits = search(query, line)
    if not hits:
        return None, "nothing matched"
    best = pick(hits, number, query)
    if best:
        return best, ""
    options = ", ".join(f'{h["productName"]} ({h.get("setName")})' for h in hits[:4])
    return None, f"ambiguous, pin it with --number. Saw: {options}"


def read_seed():
    """([raw line, ...], {productId: index into that list}).

    The # lines at the top are the file's own notes, kept as they are.
    """
    lines = [l for l in SEED.read_text(encoding="utf-8").splitlines() if l.strip()]
    return lines, {int(float(l.split("\t")[0])): i
                   for i, l in enumerate(lines) if not l.startswith("#")}


def batch_rows(path):
    """(query, number, flag) for each card line in a batch file."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = [x.strip() for x in (line.split("\t") + [""] * 3)[:3]]
        flag = f[2].lower()
        if flag not in ("", "need", "have"):
            raise SystemExit(f"{path}: third column is need, have, or blank: {line!r}")
        yield f[0], f[1], flag


def main():
    p = argparse.ArgumentParser(
        description="Add a card to product-ids.tsv, or flip whether we own it.")
    p.add_argument("card", nargs="?", default="",
                   help="card name and set, or a tcgplayer.com/product/... URL")
    p.add_argument("-n", "--number", default="",
                   help="printed number, e.g. 060/131. Pins the printing.")
    flag = p.add_mutually_exclusive_group()
    flag.add_argument("--need", action="store_true",
                      help="not owned: put it on the pull list")
    flag.add_argument("--have", action="store_true",
                      help="owned: take it off the pull list")
    p.add_argument("-j", "--japanese", action="store_true",
                   help="search the Japanese product line")
    p.add_argument("-f", "--file", help="a batch of cards, tab separated")
    p.add_argument("--dry-run", action="store_true",
                   help="say what would change, write nothing")
    args = p.parse_args()

    if args.card:
        jobs = [(args.card, args.number,
                 "need" if args.need else "have" if args.have else "")]
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            raise SystemExit(f"no such file: {path}")
        jobs = list(batch_rows(path))
    else:
        p.error("name a card, or give a batch --file")

    lines, index = read_seed()
    added = changed = 0
    problems = []

    for query, number, want in jobs:
        hit, why = resolve(query, number, args.japanese)
        if not hit:
            problems.append((query, why))
            continue
        pid = int(float(hit["productId"]))
        label = f'{hit["productName"]} ({hit.get("setName")})'
        owned = "0" if want == "need" else "1"

        if pid in index:
            row = lines[index[pid]].split("\t")
            was = row[2] if len(row) > 2 else "1"
            if want and was != owned:
                lines[index[pid]] = f"{row[0]}\t{row[1]}\t{owned}"
                changed += 1
                print(f"  {'want' if owned == '0' else 'got ':<5} {label}")
            else:
                print(f"  same  {label}")
            continue

        index[pid] = len(lines)
        lines.append(f"{pid}\t{store_url(hit)}\t{owned}")
        added += 1
        print(f"  {'add' if owned == '1' else 'want':<5} {label}")
        if len(jobs) > 1:
            time.sleep(0.4)

    for query, why in problems:
        print(f"  ??    {query}\n          {why}", file=sys.stderr)

    print(f"\n  {added} added, {changed} flipped, {len(problems)} unresolved")
    if problems and not added and not changed:
        raise SystemExit(1)
    if (added or changed) and not args.dry_run:
        SEED.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("  wrote product-ids.tsv. next: normalize_cards.py, then build.py")
    elif args.dry_run:
        print("  --dry-run, nothing written")


# Guarded because search(), resolve(), and batch_rows() are the obvious things
# to reuse from another script or a REPL, and without this an `import add_cards`
# silently runs a batch and rewrites product-ids.tsv. Not hypothetical;
# it has happened. Nothing here imports the module, so running it as a script is
# unaffected.
if __name__ == "__main__":
    main()
