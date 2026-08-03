#!/usr/bin/env python3
"""Re-fetch raw card data, normalize it, rewrite cards.csv.

Normalizations applied:
  * "Pokmon" / "Pokemon" -> "Pokémon"; "Poke Ball" -> "Poké Ball"
  * "Ability —" -> "Ability:"  (source uses both)
  * Trainer subtypes always prefixed "Trainer - "; Energy as "Energy - Basic/Special"
  * Whitespace collapsed, stray punctuation spacing tidied
  * Redundant card-number suffix stripped from name (moved to card_number)
  * type_hp_stage split into atomic card_type / hp / stage, compound kept
  * regulation_mark and standard_legal resolved per printing, not per set
  * attacks, weakness, resistance, and retreat cost carried through; the
    description field holds only the Ability, so attacks are where most of
    a card's printed text actually lives
"""
import csv, html, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
RAW = ROOT / "raw-cards.json"
API = "https://mp-search-api.tcgplayer.com/v1/search/request?q=&isList=false"
CDN = "https://tcgplayer-cdn.tcgplayer.com/product/{id}_in_1000x1000.jpg"

# Every card appearing in gengar-weezing-deck.md or charizard-deck.md.
# The last two ship in the Vivid Voltage theme deck and were never ordered.
DECK_SLUGS = {
    "me03-perfect-order/gastly", "me02-phantasmal-flames/haunter-055-094",
    "me03-perfect-order/gengar", "sv09-journey-together/koffing",
    "sv09-journey-together/weezing", "me02-phantasmal-flames/dawn",
    "me01-mega-evolution/lillies-determination-119-132", "me05-pitch-black/gwynn-078-084",
    "me01-mega-evolution/bosss-orders-ghetsis", "sv05-temporal-forces/buddy-buddy-poffin",
    "me01-mega-evolution/ultra-ball", "me01-mega-evolution/rare-candy-125-132",
    "sv-shrouded-fable/night-stretcher", "me01-mega-evolution/switch",
    "me05-pitch-black/dark-bell-075-084", "me02-phantasmal-flames/punk-helmet",
    "me01-mega-evolution/risky-ruins", "me05-pitch-black/shadowy-darkness-energy",
    "mee-mega-evolution-energies/basic-darkness-energy-007",
    "swsh04-vivid-voltage/charmander", "swsh04-vivid-voltage/charmeleon",
    "swsh04-vivid-voltage/charizard", "sv-prismatic-evolutions/eevee",
    "sv-prismatic-evolutions/flareon", "swsh04-vivid-voltage/leon",
    "sv-prismatic-evolutions/professors-research-professor-oak",
    "battle-academy/welder-189-214-25-charizard-stamped",
    "swsh09-brilliant-stars/kindler", "swsh07-evolving-skies/zinnias-resolve",
    "sv-paldean-fates/nest-ball", "swsh01-sword-and-shield-base-set/evolution-incense",
    "swsh01-sword-and-shield-base-set/ordinary-rod", "swsh09-brilliant-stars/magma-basin",
    "swsh01-sword-and-shield-base-set/sudowoodo",
    "mee-mega-evolution-energies/basic-fire-energy-002",
}

rows = [l.split("\t") for l in (ROOT / "product-ids.tsv").read_text().splitlines() if l.strip()]
pid_to_url = {int(float(p)): u for p, u in rows}
ids = list(pid_to_url)


def fetch(chunk):
    body = json.dumps({
        "algorithm": "sales_synonym_v2", "from": 0, "size": len(chunk),
        "filters": {"term": {"productLineName": ["pokemon"], "productId": chunk},
                    "range": {}, "match": {}},
        "listingSearch": {"context": {"cart": {}},
                          "filters": {"term": {}, "range": {},
                                      "exclude": {"channelExclusion": 0}}},
        "context": {"cart": {}, "shippingCountry": "US"},
        "sort": {"field": "product-sorting-name", "order": "asc"}})
    out = subprocess.run(["curl", "-s", API, "-H", "Content-Type: application/json",
                          "-H", "User-Agent: Mozilla/5.0", "-d", body, "--max-time", "40"],
                         capture_output=True, text=True).stdout
    return json.loads(out)["results"][0]["results"]


if RAW.exists():
    products = {int(k): v for k, v in json.loads(RAW.read_text()).items()}
else:
    products = {}
    for i in range(0, len(ids), 40):
        for p in fetch(ids[i:i + 40]):
            products[int(float(p["productId"]))] = p
        print(f"  fetched {len(products)}/{len(ids)}", file=sys.stderr)
        time.sleep(1.0)
    RAW.write_text(json.dumps({str(k): v for k, v in products.items()}))


def accents(s):
    s = re.sub(r"\bPok[eé]?mon\b", "Pokémon", s)
    s = re.sub(r"\bPokmon\b", "Pokémon", s)
    s = re.sub(r"\bPoke Ball\b", "Poké Ball", s)
    return s


def clean_text(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace("\r", " ").replace("\n", " ")
    s = accents(s)
    s = re.sub(r"\s*•\s*", " • ", s)
    s = re.sub(r"\s+", " ", s).strip()          # collapse first, so ^ anchors work
    s = re.sub(r"^Ability\s*[—–-]\s*", "Ability: ", s)
    s = re.sub(r"\s+([,.;:)])", r"\1", s)
    return s


def clean_attack(s):
    """Tidy an attack, keeping the split between its header and its effect text.

    The source reads "[1RR] Flamethrower (50)\\r\\n<br>Discard 1 Fire Energy...".
    That <br> is the only thing separating the cost and damage from the rules
    text, so it becomes " - " before the tag stripper eats it.
    """
    if not s:
        return ""
    s = re.sub(r"\s*(?:\r?\n)?\s*<br\s*/?>\s*", " - ", str(s))
    return clean_text(s)


def strip_number(name, number):
    """Remove the card number from the product name; card_number carries it.

    Handles it appearing mid-name ("Welder - 189/214 (#25 ...)") and
    zero-padded against an unpadded source value ("- 007" vs number "7").
    """
    variants = set()
    if number:
        head, _, tail = number.partition("/")
        bare = head.lstrip("0") or head
        for f in {head, bare, bare.zfill(2), bare.zfill(3)}:
            variants.add(f"{f}/{tail}" if tail else f)
            variants.add(f)
    for v in sorted(filter(None, variants), key=len, reverse=True):
        name = re.sub(r"\s*-\s*" + re.escape(v) + r"(?=\s|\(|$)", " ", name)
        name = re.sub(r"\s*\(" + re.escape(v) + r"\)", " ", name)
    name = re.sub(r"\s*-\s*SWSH\d+(?=\s|\(|$)", " ", name)
    return re.sub(r"\s+", " ", name).strip()


ENERGY_TYPE = {"G": "Grass", "R": "Fire", "W": "Water", "L": "Lightning",
               "P": "Psychic", "F": "Fighting", "D": "Darkness", "M": "Metal",
               "Y": "Fairy", "N": "Dragon"}


def type_from_attack(ca):
    """Fallback for the handful of old cards where TCGplayer has no cardTypeB."""
    for k in ("attack1", "attack2", "attack3", "attack4"):
        m = re.match(r"\s*\[([^\]]+)\]", str(ca.get(k) or ""))
        if m:
            for ch in m.group(1):
                if ch in ENERGY_TYPE:
                    return ENERGY_TYPE[ch]
    return ""


def expand_type_code(s):
    """Spell out TCGplayer's weakness/resistance shorthand.

    "Dx2" -> "Darkness ×2", "F-30" -> "Fighting -30", bare "W" -> "Water".
    Resistance comes back as the literal string "None" on cards that have
    none, which is not the same as the field being absent, so it is dropped
    here rather than surviving into the CSV as text.
    """
    s = str(s or "").strip()
    if not s or s.lower() == "none":
        return ""
    m = re.fullmatch(r"([A-Z])\s*(?:x\s*(\d+)|([+-]\s*\d+))?", s)
    if not m:
        return s
    letter, mult, mod = m.groups()
    t = ENERGY_TYPE.get(letter, letter)
    if mult:
        return f"{t} ×{mult}"
    if mod:
        return f"{t} {re.sub(r'\s+', '', mod)}"
    return t


# --- Standard legality -------------------------------------------------------
# The 2026-27 Standard format took effect 10 April 2026: H, I, and J are legal
# and G and everything older rotated out. Marks come from regulation-marks.json,
# which fetch_regulation.py builds, because legality is a property of the
# printing rather than of the set. Prismatic Evolutions is the proof: Flareon
# 013 carries G and Flareon ex 014 carries H, in the same set.
LEGAL_MARKS = {"H", "I", "J"}

# Temporal Forces is the earliest set to carry an H mark, so anything printed
# before it rotated out no matter what it says. This resolves the whole pre-2024
# back catalogue without needing a mark for any of it.
FIRST_H_SET_RELEASE = "2024-03-22"

# Sets with no upstream data and no help from the release date. The Trick or
# Trade bundles are Halloween promo reprints; xero confirmed they are too old to
# be legal. MEE is absent too but needs no entry: it is Basic Energy, which
# never rotates.
PRE_ROTATION_SETS = {"BTA", "TTBB", "TTBB23", "TTBB24"}

REG_MARKS = {}
if (ROOT / "regulation-marks.json").exists():
    REG_MARKS = json.loads((ROOT / "regulation-marks.json").read_text()).get("marks", {})


def reg_key(set_code, number):
    n = str(number or "").split("/")[0].strip()
    return f"{set_code}/{n.lstrip('0') or n}"


def legality(set_code, number, ctype, released, name=""):
    """(regulation_mark, standard_legal) for one card.

    standard_legal is "yes", "no", or "unknown". Unknown is deliberate: a card
    whose mark could not be resolved is not the same as a card known to be
    illegal, and quietly calling it "no" would hide gaps in the lookup.
    """
    # Basic Energy is legal from any set and carries no mark at all. Fairy is
    # the one exception, retired along with the type.
    if ctype == "Energy - Basic":
        return "", "no" if "fairy" in name.lower() else "yes"
    mark = REG_MARKS.get(reg_key(set_code, number), "")
    if mark:
        return mark, "yes" if mark in LEGAL_MARKS else "no"
    if released and released[:10] < FIRST_H_SET_RELEASE:
        return "", "no"
    if set_code in PRE_ROTATION_SETS:
        return "", "no"
    return "", "unknown"


TRAINER_SUB = {"item", "supporter", "stadium", "pokémon tool", "pokemon tool", "tool"}


def norm_type(card_type_b, hp, stage):
    t = accents((card_type_b or "").strip())
    low = t.lower().replace("trainer - ", "").strip()
    if low in TRAINER_SUB:
        sub = "Pokémon Tool" if "tool" in low else low.title()
        return f"Trainer - {sub}", "", ""
    if low in ("basic energy", "special energy"):
        return f"Energy - {low.split()[0].title()}", "", ""
    if low.endswith(" energy"):
        return f"Energy - {low[:-7].title()}", "", ""
    return t, str(hp or "").strip(), accents(str(stage or "").strip())


records = []
for pid in ids:
    p = products.get(pid)
    url = pid_to_url[pid]
    slug = url.split("/pokemon/", 1)[1]
    card_slug = slug.split("/")[-1]
    ca = (p.get("customAttributes") or {}) if p else {}

    number = str(ca.get("number") or "").strip()
    name = accents((p.get("productName") or "").strip())
    name = strip_number(name, number)

    ctb = ca.get("cardTypeB")
    if not ctb and "Pokemon" in (ca.get("cardType") or []):
        ctb = type_from_attack(ca)
        if ctb:
            print(f"  note: derived type {ctb!r} from attack cost for {name}", file=sys.stderr)
    ctype, hp, stage = norm_type(ctb, ca.get("hp"), ca.get("stage"))
    mark, legal = legality(p.get("setCode") if p else "", number, ctype,
                           ca.get("releaseDate") or "", name)
    ths = " / ".join(x for x in (ctype, hp, stage) if x)

    img_name = f"{pid}_{card_slug}.jpg"
    if not (ASSETS / img_name).exists():
        rc = subprocess.run(["curl", "-s", "-f", "-o", str(ASSETS / img_name),
                             CDN.format(id=pid), "--max-time", "40"]).returncode
        if rc != 0:
            print(f"  WARNING: image download failed for {name}", file=sys.stderr)
            img_name = ""
        else:
            print(f"  downloaded {img_name}", file=sys.stderr)

    records.append({
        "name": name,
        "set_name": accents((p.get("setName") or "").strip()),
        "card_number": number,
        "rarity": accents((p.get("rarityName") or "").strip()) if p else "",
        "card_type": ctype,
        "hp": hp,
        "stage": stage,
        "type_hp_stage": ths,
        "card_text": clean_text(ca.get("description")),
        "attack1": clean_attack(ca.get("attack1")),
        "attack2": clean_attack(ca.get("attack2")),
        "attack3": clean_attack(ca.get("attack3")),
        "attack4": clean_attack(ca.get("attack4")),
        "weakness": expand_type_code(ca.get("weakness")),
        "resistance": expand_type_code(ca.get("resistance")),
        "retreat_cost": str(ca.get("retreatCost") or "").strip(),
        "regulation_mark": mark,
        "standard_legal": legal,
        "image_file": img_name,
        "category": "deck" if slug in DECK_SLUGS else "collection",
        "source_url": url,
    })

records.sort(key=lambda r: (r["category"], r["set_name"], r["name"]))
cols = ["name", "set_name", "card_number", "rarity", "card_type", "hp", "stage",
        "type_hp_stage", "card_text", "attack1", "attack2", "attack3", "attack4",
        "weakness", "resistance", "retreat_cost",
        "regulation_mark", "standard_legal",
        "image_file", "category", "source_url"]
with open(ROOT / "cards.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(records)

print(f"rows={len(records)} deck={sum(r['category']=='deck' for r in records)} "
      f"collection={sum(r['category']=='collection' for r in records)}")
