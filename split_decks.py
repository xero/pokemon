#!/usr/bin/env python3
"""Copy cards.csv into fire.csv and dark.csv, each pruned to that deck's cards.

cards.csv is never modified. Four Trainers sit in both decks and so appear in
both output files: Boss's Orders, Rare Candy, Ultra Ball, and Switch.
"""
import csv, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "cards.csv"

DARK = {  # dark.md, Xero's Gengar Gang
    "me03-perfect-order/gastly",
    "me02-phantasmal-flames/haunter-055-094",
    "me03-perfect-order/gengar",
    "sv09-journey-together/koffing",
    "sv09-journey-together/weezing",
    "me02-phantasmal-flames/dawn",
    "me01-mega-evolution/lillies-determination-119-132",
    "me05-pitch-black/gwynn-078-084",
    "me01-mega-evolution/bosss-orders-ghetsis",
    "sv05-temporal-forces/buddy-buddy-poffin",
    "me01-mega-evolution/ultra-ball",
    "me01-mega-evolution/rare-candy-125-132",
    "sv-shrouded-fable/night-stretcher",
    "me01-mega-evolution/switch",
    "me05-pitch-black/dark-bell-075-084",
    "me02-phantasmal-flames/punk-helmet",
    "me01-mega-evolution/risky-ruins",
    "me05-pitch-black/shadowy-darkness-energy",
    "mee-mega-evolution-energies/basic-darkness-energy-007",
}

FIRE = {  # fire.md, Fox's Fire Force
    "swsh04-vivid-voltage/charmander",
    "swsh04-vivid-voltage/charmeleon",
    "swsh04-vivid-voltage/charizard",
    "sv-prismatic-evolutions/eevee",
    "sv-prismatic-evolutions/flareon",
    "swsh01-sword-and-shield-base-set/sudowoodo",
    "swsh04-vivid-voltage/leon",
    "sv-prismatic-evolutions/professors-research-professor-oak",
    "me01-mega-evolution/bosss-orders-ghetsis",
    "battle-academy/welder-189-214-25-charizard-stamped",
    "swsh09-brilliant-stars/kindler",
    "swsh07-evolving-skies/zinnias-resolve",
    "me01-mega-evolution/rare-candy-125-132",
    "me01-mega-evolution/ultra-ball",
    "sv-paldean-fates/nest-ball",
    "me01-mega-evolution/switch",
    "swsh01-sword-and-shield-base-set/evolution-incense",
    "swsh01-sword-and-shield-base-set/ordinary-rod",
    "swsh09-brilliant-stars/magma-basin",
    "mee-mega-evolution-energies/basic-fire-energy-002",
}


def slug(url):
    # Japanese products sit on /pokemon-japan/ rather than /pokemon/.
    return re.sub(r"^.*?/pokemon(?:-japan)?/", "", url)


rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
cols = list(rows[0])

for name, keep in (("fire.csv", FIRE), ("dark.csv", DARK)):
    dest = ROOT / name
    shutil.copyfile(SRC, dest)                      # exact copy first
    picked = [r for r in rows if slug(r["source_url"]) in keep]
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(picked)
    found = {slug(r["source_url"]) for r in picked}
    missing = keep - found
    print(f"{name}: {len(picked)}/{len(keep)} rows"
          + (f"  *** MISSING {sorted(missing)}" if missing else ""))
    if missing:
        sys.exit(1)

print(f"cards.csv unchanged: {len(rows)} rows")
print(f"shared by both decks: {sorted(FIRE & DARK)}")
