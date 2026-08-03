#!/usr/bin/env python3
"""Fetch per-card regulation marks from pokemontcg.io, cache to regulation-marks.json.

TCGplayer's search API carries no legality data of any kind, so the mark has to
come from somewhere else. It has to be resolved per card, not per set:
Prismatic Evolutions ships Flareon 013 with a G mark and Flareon ex 014 with an
H, so a set-level lookup table would call real cards legal that are not.

The upstream API is unreliable, returning empty 500s and hanging connections in
bursts, so every set is retried with backoff and finished sets are recorded in
the cache. Rerunning only fetches what is still missing; it is safe to run the
script repeatedly until it reports nothing outstanding.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw-cards.json"
DEST = ROOT / "regulation-marks.json"
API = "https://api.pokemontcg.io/v2"
ATTEMPTS = 4

# Our TCGplayer setCode -> pokemontcg.io set id. Their ptcgoCode agrees with us
# often enough to be tempting and not often enough to rely on, so this is
# written out by hand.
SET_IDS = {
    "BS": "base1", "BS2": "base4", "FO": "base3", "CG": "ex14",
    "PLS": "bw8", "FCO": "xy10", "EVO": "xy12",
    "SM03": "sm3", "SM04": "sm4", "SM9": "sm9", "HIF": "sm115",
    "SWSD": "swshp", "SWSH01": "swsh1", "SWSH04": "swsh4", "SHF": "swsh45",
    "SWSH06": "swsh6", "SWSH07": "swsh7", "SWSH08": "swsh8", "SWSH09": "swsh9",
    "PGO": "pgo", "OBF": "sv3", "MEW": "sv3pt5", "PAR": "sv4", "PAF": "sv4pt5",
    "TEF": "sv5", "TWM": "sv6", "SFA": "sv6pt5", "SCR": "sv7", "PRE": "sv8pt5",
    "JTG": "sv9", "DRI": "sv10",
    "MEG": "me1", "PFL": "me2", "ASC": "me2pt5", "POR": "me3", "CRI": "me4",
    "PBL": "me5",
    # No upstream equivalent: BTA (Battle Academy), MEE (Mega Evolution
    # Energies), and the three Trick or Trade bundles. Handled in
    # normalize_cards.py, which knows why each one is safe to decide without.
}


def get(path):
    for i in range(ATTEMPTS):
        out = subprocess.run(["curl", "-s", f"{API}/{path}", "--max-time", "40"],
                             capture_output=True, text=True).stdout
        try:
            d = json.loads(out)
            if "data" in d:
                return d
        except json.JSONDecodeError:
            pass
        if i < ATTEMPTS - 1:
            time.sleep(3 * 2 ** i)
    return None


def norm(number):
    """"033/192" and "33" and "013" all have to collide on one key."""
    n = str(number or "").split("/")[0].strip()
    return n.lstrip("0") or n


cache = json.loads(DEST.read_text()) if DEST.exists() else {}
marks = cache.get("marks", {})
done = cache.get("sets", {})

# Temporal Forces is the earliest set to carry an H mark, so nothing printed
# before it can be Standard legal today and nothing before it is worth a
# request. normalize_cards.py resolves those to "no" on release date alone.
FIRST_H_SET_RELEASE = "2024-03-22"

products = json.loads(RAW.read_text()).values()
released = {}
for p in products:
    rd = (p.get("customAttributes") or {}).get("releaseDate") or ""
    released[p.get("setCode")] = max(released.get(p.get("setCode"), ""), rd[:10])

# Pre-H sets are skipped by default because their legality is already settled by
# release date. Pass --all to fetch them anyway, which fills in the mark letter
# for the back catalogue so the CSV can show why a card is out, not just that it
# is. Costs a dozen or so extra requests and changes no verdicts.
fetch_all = "--all" in sys.argv

wanted = sorted(c for c, rd in released.items()
                if fetch_all or rd >= FIRST_H_SET_RELEASE)
old = sorted(c for c, rd in released.items() if rd < FIRST_H_SET_RELEASE)
todo = [c for c in wanted if c in SET_IDS and c not in done]
skipped = [c for c in wanted if c not in SET_IDS]

print(f"{len(released)} sets total, {len(wanted)} in scope"
      + ("" if fetch_all else f" ({len(old)} pre-H skipped)")
      + f", {len(todo)} to fetch, {len(skipped)} with no upstream set",
      file=sys.stderr)

failed = []
for code in todo:
    sid = SET_IDS[code]
    d = get(f"cards?q=set.id:{sid}&select=number,regulationMark&pageSize=250")
    if d is None:
        print(f"  {code:<8}{sid:<10}FAILED after {ATTEMPTS} tries", file=sys.stderr)
        failed.append(code)
        continue
    n = 0
    for c in d["data"]:
        if c.get("regulationMark"):
            marks[f"{code}/{norm(c['number'])}"] = c["regulationMark"]
            n += 1
    done[code] = {"id": sid, "cards": len(d["data"]), "marked": n}
    print(f"  {code:<8}{sid:<10}{len(d['data']):>4} cards, {n:>4} marked",
          file=sys.stderr)
    DEST.write_text(json.dumps({"sets": done, "marks": marks},
                               indent=0, sort_keys=True))
    time.sleep(1.0)

DEST.write_text(json.dumps({"sets": done, "marks": marks}, indent=0, sort_keys=True))
print(f"regulation-marks.json: {len(marks)} marked cards across {len(done)} sets")
if failed:
    print(f"still outstanding, rerun to retry: {', '.join(failed)}")
if skipped:
    print(f"no upstream set (decided in normalize_cards.py): {', '.join(skipped)}")
