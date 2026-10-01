#!/usr/bin/env python3
"""Re-run the parser on the logs in files/ and check what it should find.

Each check is a fact a person confirmed by reading the log. Run this after any
change to scripts/parse_log.py; a failure means the ledger drifted.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import parse_log  # noqa: E402

DECK = "dark-gang.md"
COMMIT = "df7ccfe"   # the list these three games were played against


def load(name):
    pool = parse_log.Pool()
    decklib, _ = parse_log.registered_decks()
    for q, card, hint, num in parse_log.deck_list(decklib, DECK, COMMIT):
        pool.pin(card, hint, num)
    return parse_log.Game((HERE / "files" / name).read_text(encoding="utf-8"), pool)


def flags(game, n):
    return next((t.flags for t in game.turns if t.owner == game.me and t.n == n), [])


def events(game, owner, n):
    who = game.me if owner == "you" else game.opp
    return next((t.events for t in game.turns if t.owner == who and t.n == n), [])


def board(game, n):
    return next((t.end_board for t in game.turns if t.owner == game.me and t.n == n), [])


def hand(game, n):
    return next((t.end_hand for t in game.turns if t.owner == game.me and t.n == n), [])


zac, kan, oge = load("zacian-loss.txt"), load("kangaskhan-win.txt"), load("ogerpon-win.txt")
zor = load("zoroark-win.txt")
met = load("metagross-win.txt")
igg = load("igglybuff-win.txt")
mir = load("gengar-mirror-loss.txt")
cru = load("crustle-loss.txt")

CHECKS = [
    # the Hop's Zacian loss
    ("zacian: you are xer0style, going second", lambda: (zac.me, zac.first) == ("xer0style", False)),
    ("zacian: loss, 3 Prizes to 6", lambda: (zac.result, zac.prizes[zac.me], zac.prizes[zac.opp]) == ("loss", 3, 6)),
    ("zacian: Hilda is a search, not a draw", lambda: "searched Gengar ex, Neo Upper Energy" in events(zac, "you", 1)),
    ("zacian: hand after turn 1", lambda: hand(zac, 1) == sorted(
        ["Basic Darkness Energy", "Basic Darkness Energy", "Boss's Orders", "Gengar ex", "Gengar ex", "Neo Upper Energy"])),
    ("zacian: turn 2 strands a Gengar ex holding Neo Upper",
     lambda: any("loaded on the Bench: Gengar ex[Neo Upper Energy]" in f for f in flags(zac, 2))),
    ("zacian: turn 4 holds an Energy with no attachment",
     lambda: any(f.startswith("held Basic Darkness Energy") for f in flags(zac, 4))),
    ("zacian: a Toxel from a Prize after the attack isn't a held Basic",
     lambda: not any("Toxel" in f for f in flags(zac, 4))),
    ("zacian: turn 8 strands a Gengar ex behind the Mega",
     lambda: any("loaded on the Bench: Gengar ex[Darkness, Darkness]" in f for f in flags(zac, 8))),
    ("zacian: a Gastly or Haunter with one Energy is not 'loaded'",
     lambda: not any("Haunter" in f or "Gastly" in f for n in (6, 7) for f in flags(zac, n))),
    ("zacian: the Gengar ex KO line adds to 370",
     lambda: any("lost Gengar ex (took 60 + 180 + 130 = 370 of 280 HP)" in e for e in events(zac, "opp", 6))),
    ("zacian: a Stadium bump isn't a hand discard", lambda: not zac.warnings),

    # the Mega Kangaskhan win
    ("kangaskhan: win on a timeout, 3 Prizes to 0",
     lambda: (kan.result, kan.prizes[kan.me], kan.prizes[kan.opp]) == ("win", 3, 0) and "inactive" in kan.how),
    ("kangaskhan: the mulligan draw reaches the hand", lambda: "Dawn" in kan.random_seen),
    ("kangaskhan: the second Toxtricity's Surge went unused on turn 3",
     lambda: any("Sinister Surge used 1 of 2" in f for f in flags(kan, 3))),
    ("kangaskhan: Toxel held on turn 1 with room on the Bench",
     lambda: any(f.startswith("held Toxel") for f in flags(kan, 1))),
    ("kangaskhan: Musculature is not a missed attack", lambda: not any("no attack" in f for f in flags(kan, 1))),
    ("kangaskhan: Lillie's shuffle-back leaves the hand", lambda: "Grimsley's Move" in hand(kan, 3)
     and hand(kan, 3).count("Grimsley's Move") == 1),
    ("kangaskhan: no tracking warnings", lambda: not kan.warnings),

    # the Ogerpon and Igglybuff win
    ("ogerpon: an accented handle parses", lambda: oge.opp == "Brunãobr"),
    ("ogerpon: win on Prizes, 6 to 4, going first",
     lambda: (oge.result, oge.prizes[oge.me], oge.prizes[oge.opp], oge.first) == ("win", 6, 4, True)),
    ("ogerpon: turn 1 going first is never flagged for no attack", lambda: not flags(oge, 1)),
    ("ogerpon: Neo Upper held on turn 3", lambda: any(f.startswith("held Neo Upper") for f in flags(oge, 3))),
    ("ogerpon: Lisia's Appeal swaps your Active", lambda: board(oge, 3)[0].startswith("Toxel")),
    ("ogerpon: Void Gale's attach line is a move", lambda: board(oge, 6)[0] == "Mega Gengar ex[Darkness]"),
    ("ogerpon: Handheld Fan moves Energy off your attacker",
     lambda: board(oge, 7) == ["Haunter[Darkness]", "Mega Gengar ex[Darkness]", "Toxel[Darkness]"]),
    ("ogerpon: Janine's reaches both Megas", lambda: board(oge, 8) ==
     ["Mega Gengar ex[Darkness]", "Mega Gengar ex[Darkness, Darkness, Darkness]"]),
    ("ogerpon: no tracking warnings", lambda: not oge.warnings),

    # the N's Zoroark ex win, conceded
    ("zoroark: conceded win at 5 Prizes each", lambda: (zor.result, zor.prizes[zor.me], zor.prizes[zor.opp]) == ("win", 5, 5)
     and "conceded" in zor.how),
    ("zoroark: Grimsley's benches the Pokémon it finds", lambda: "benched Toxtricity" in events(zor, "you", 3)
     and not any("played it" in c for c in zor.revealed)),
    ("zoroark: Energy Recycler's shuffle-back never touches the hand", lambda: not zor.warnings),
    ("zoroark: Punk Helmet's counters land on your dog",
     lambda: any("lost Okidogi ex (took 10 + 10 + 40 + 10 + 10 + 40 + 10 + 170 = 300 of 250 HP)" in e for e in events(zor, "opp", 5))),
    ("zoroark: Munkidori's moved counters land on your Pokémon",
     lambda: any("lost Toxtricity (took 20 + 20 + 20 + 30 + 250 = 340 of 140 HP)" in e for e in events(zor, "opp", 8))),
    ("zoroark: a Fainting Spell KO is your Prize on their turn",
     lambda: ("you", 7, 2, "N's Zoroark ex", "Opp") in zor.prize_log),
    ("zoroark: a turn cut short by a concession isn't flagged",
     lambda: flags(zor, 12) == ["game ended before this turn's attack"]),
    ("zoroark: the Boss-stalled turn 5 strands the loaded dog",
     lambda: any("loaded on the Bench: Okidogi ex" in f for f in flags(zor, 5))),
    ("numbers: Chaotic Pain did the Zacian game's work",
     lambda: zac.attackers["Gengar ex: Chaotic Pain"] == {"attacks": 3, "KOs": 3, "Prizes": 3}),
    ("numbers: a Fainting Spell KO counts for Gengar ex",
     lambda: zor.attackers["Gengar ex: Fainting Spell"] == {"KOs": 1, "Prizes": 2}),
    ("numbers: Toxtricity under Concealment gave up nothing",
     lambda: zor.losses["Toxtricity"] == {"KO'd": 2}),
    ("numbers: Prize flow names the Gengar the opponent took, not the Zoroark",
     lambda: ("they", 7, 2, "Gengar ex", "Opp") in zor.prize_log),
    ("numbers: both Megas sat in hand turns 4 to 8 in the Zacian game",
     lambda: ("Mega Gengar ex", 1, 4, 8) in zac.stuck()),
    # the Steven's Metagross win, after your own mulligan
    ("metagross: your mulligan empties the hand ledger", lambda: met.hand_unknown and "Hilda" not in hand(met, 1)),
    ("metagross: an unknown kept hand raises no warnings", lambda: not met.warnings),
    ("metagross: a Weakness line keeps the attack name clean",
     lambda: met.attackers["Okidogi ex: Chain-Crazed"] == {"attacks": 1, "KOs": 1, "Prizes": 2}),
    ("metagross: Happy Switch takes a benched donor, not the attacker about to swing",
     lambda: board(met, 4) == ["Gengar ex[Darkness, Darkness]", "Toxel", "Gastly", "Blissey ex", "Toxtricity", "Okidogi ex[Darkness]"]),
    # the Igglybuff win, by concession at 5-5
    ("igglybuff: a Prize printed before its KO line still names the KO",
     lambda: ("you", 3, 1, "Igglybuff", "You") in igg.prize_log),
    ("igglybuff: Battle Cage and Hide 'n' Sneak lines don't move Chaotic Pain's target",
     lambda: igg.attackers["Gengar ex: Chaotic Pain"] == {"attacks": 4, "KOs": 4, "Prizes": 4}),
    ("igglybuff: the Surge counters are what put the Gengar ex over",
     lambda: any("lost Gengar ex (took 20 + 150 + 120 = 290 of 280 HP)" in e for e in events(igg, "opp", 6))),
    ("igglybuff: turn 3 skipped Sinister Surge", lambda: any("Sinister Surge used 0 of 1" in f for f in flags(igg, 3))),
    ("igglybuff: a concession on their turn ends the game as a win", lambda: (igg.result, igg.prizes[igg.me]) == ("win", 5)),
    # the Mega Gengar mirror loss, where both sides run Toxel, Toxtricity, and Mega Gengar ex
    ("mirror: loss, 4 Prizes to 6, going second",
     lambda: (mir.result, mir.prizes[mir.me], mir.prizes[mir.opp], mir.first) == ("loss", 4, 6, False)),
    ("mirror: their Chaotic Pain lands on your Toxel, though they bench one too",
     lambda: any("lost Toxel (took 130 of 70 HP)" in e for e in events(mir, "opp", 2))),
    ("mirror: your own Surge counters are what put Toxtricity in Pain range",
     lambda: any("lost Toxtricity (took 20 + 130 = 150 of 140 HP)" in e for e in events(mir, "opp", 6))),
    ("mirror: their Surge onto their Mega stays off yours",
     lambda: not any("counters on Mega Gengar ex" in e for e in events(mir, "opp", 7))),
    ("mirror: turn 3 skipped Sinister Surge", lambda: any("Sinister Surge used 0 of 1" in f for f in flags(mir, 3))),
    # the Crustle loss, Lucky Haunt's list, conceded at 0-2
    ("crustle: a concession on your turn is a loss, 0 Prizes to 2",
     lambda: (cru.result, cru.prizes[cru.me], cru.prizes[cru.opp]) == ("loss", 0, 2) and "conceded" in cru.how),
    ("crustle: Lucky Attachment's Energy leaves the hand", lambda: hand(cru, 1).count("Basic Darkness Energy") == 1),
    ("crustle: a one-card Lillie's shuffle leaves the hand", lambda: "AZ's Tranquility" not in hand(cru, 3)),
    ("crustle: Mist Energy stopped Chaotic Pain, so it found no target",
     lambda: cru.attackers["Gengar ex: Chaotic Pain"] == {"attacks": 1}
     and not any("counters" in e for e in events(cru, "you", 3))),
    ("crustle: no Energy in hand on turns 5 and 6, so no held-Energy flag",
     lambda: not any(f.startswith("held Basic Darkness Energy") for n in (5, 6) for f in flags(cru, n))),
    ("dedupe: straight and curly apostrophes hash the same", lambda: parse_log.body_hash("a’s\n\nb") == parse_log.body_hash("a's\nb")),
]

failed = 0
for name, check in CHECKS:
    try:
        ok = bool(check())
    except Exception as e:  # a crash is a failure with a reason
        ok, name = False, f"{name} (raised {e!r})"
    failed += not ok
    print(f"{'✓' if ok else '✗'} {name}")
print(f"\n{len(CHECKS) - failed} of {len(CHECKS)} passed")
sys.exit(1 if failed else 0)
