#!/usr/bin/env python3
"""Read Pokémon TCG Live battle logs: archive them, ledger them, total them.

    parse_log.py save LOG [--deck SRC] [--mode M] [--changes TXT] [--opp-deck TXT]
                          [--date YYYY-MM-DD] [--notes TXT] [--me NAME]
    parse_log.py report LOG
    parse_log.py summary

save     writes LOG into logs/ under a dated name, with a metadata header on top.
         It matches the cards you revealed against every registered deck, stamps
         the commit that last changed that deck's list, and names any card you
         played that the list doesn't have. A raw log already inside logs/ is
         replaced by the archived copy.
report   prints the game turn by turn from your side: your hand as the log
         reveals it, what you attached, what attacked, and the flags worth a
         look (a held Energy, an unused Ability, a turn with no attack, a loaded
         attacker stuck on the Bench, and how lucky the draws were).
summary  totals every archived log by deck, list commit, and list changes.

The log never names the printing, so everything here works by card name.
"""
import argparse
import collections
import glob
import hashlib
import json
import math
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LOGS = ROOT / "logs"
sys.path.insert(0, str(ROOT))

FIELDS = ["date", "player", "deck", "commit", "changes", "unlisted", "mode",
          "opponent", "opp_deck", "opp_pokemon", "went", "result", "how",
          "prizes", "turns", "notes"]
ACTIVE, BENCH = "active", "bench"
ALL = "ALL"


def norm(s):
    """Fold accents and curly quotes so Live, the pool, and the repo agree."""
    s = unicodedata.normalize("NFKD", s.replace("’", "'"))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


# ---------------------------------------------------------------- card data
class Pool:
    """Card text by name from the newest legal-cards snapshot."""

    def __init__(self):
        files = sorted(glob.glob(str(ROOT / "legal-cards-*.json")))
        cards = json.load(open(files[-1]))["cards"] if files else []
        self.by_name = collections.defaultdict(list)
        self.effects = {}
        for c in cards:
            self.by_name[norm(c["name"])].append(c)
            rules = " ".join(c.get("rules") or [])
            if rules:
                self.effects.setdefault(norm(c["name"]), rules)
            for a in c.get("abilities") or []:
                self.effects.setdefault(norm(a["name"]), a.get("text", ""))
            for a in c.get("attacks") or []:
                self.effects.setdefault(norm(a["name"]), a.get("text", ""))
        self.ability_names = {norm(a["name"]) for c in cards for a in c.get("abilities") or []}
        self.pins = {}

    def pin(self, name, set_name, number):
        """Prefer the printing the deck list names when a name has several."""
        for c in self.by_name.get(norm(name), []):
            if norm(c["set"]["name"]) == norm(set_name) and c["number"].lstrip("0") == str(number).lstrip("0"):
                self.pins[norm(name)] = c
                return

    def card(self, name):
        n = norm(name)
        if n in self.pins:
            return self.pins[n]
        hits = self.by_name.get(n)
        return hits[0] if hits else None

    def kind(self, name):
        """Pokemon, Supporter, Item, Tool, Stadium, Energy, or '?'."""
        if re.fullmatch(r"basic \w+ energy", norm(name)):
            return "Energy"
        c = self.card(name)
        if not c:
            return "?"
        if c["supertype"] != "Trainer":
            return "Pokemon" if c["supertype"].startswith("Pok") else c["supertype"]
        subs = c.get("subtypes") or []
        for k, v in (("Supporter", "Supporter"), ("Stadium", "Stadium"),
                     ("Pokémon Tool", "Tool"), ("Item", "Item")):
            if k in subs:
                return v
        return "Trainer"

    def stage(self, name):
        c = self.card(name) or {}
        subs = c.get("subtypes") or []
        return 2 if "Stage 2" in subs else 1 if "Stage 1" in subs else 0

    def text(self, name):
        return self.effects.get(norm(name), "")


# ---------------------------------------------------------------- energy math
def energy_units(pool, ecard, holder):
    """What one attached Energy card pays, as a list of sets of types."""
    m = re.fullmatch(r"Basic (\w+) Energy", ecard)
    if m:
        return [{m.group(1)}]
    txt = pool.text(ecard)
    st = pool.stage(holder)
    if "attached to a Stage 2" in txt and "only 2 Energy" in txt:
        return [{ALL}, {ALL}] if st == 2 else [{"Colorless"}]
    if "attached to an Evolution" in txt and "ColorlessColorlessColorless" in txt:
        return [{"Colorless"}] * 3 if st > 0 else [{"Colorless"}]
    if "attached to a Basic" in txt and "every type" in txt:
        return [{ALL}] if st == 0 else [{"Colorless"}]
    if "every type" in txt:
        return [{ALL}]
    m = re.search(r"provides (\w+) Energy", txt)
    return [{m.group(1)}] if m else [{"Colorless"}]


def can_pay(cost, units):
    units = [set(u) for u in units]
    for t in [c for c in cost if c != "Colorless"]:
        pick = next((u for u in units if t in u), None) or next((u for u in units if ALL in u), None)
        if pick is None:
            return False
        units.remove(pick)
    return len(units) >= cost.count("Colorless")


REAL_HIT = 100   # below this an attack is a poke, not a reason to call a body loaded


def hit_size(a):
    """Base damage, or 10 per damage counter the attack places."""
    m = re.match(r"(\d+)", a.get("damage") or "")
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+) damage counters", a.get("text") or "")
    return 10 * int(m.group(1)) if m else 0


def ready_attacks(pool, mon, floor=REAL_HIT):
    """The attacks of at least floor damage this Pokémon could pay for now."""
    c = pool.card(mon.name)
    if not c:
        return []
    units = [u for e in mon.energy for u in energy_units(pool, e, mon.name)]
    return [a["name"] for a in c.get("attacks") or []
            if hit_size(a) >= floor and can_pay(a.get("cost") or [], units)]


def energy_short(pool, mon, most=4):
    """(Energy needed, attack) for the cheapest real attack this Pokémon can't pay yet."""
    c = pool.card(mon.name) if mon else None
    if not c:
        return None
    units = [u for e in mon.energy for u in energy_units(pool, e, mon.name)]
    real = [a for a in c.get("attacks") or [] if hit_size(a) >= REAL_HIT]
    for k in range(1, most + 1):
        for a in real:
            if can_pay(a.get("cost") or [], units + [{ALL}] * k):
                return k, a["name"]
    return None


# ---------------------------------------------------------------- the model
class Mon:
    def __init__(self, name, loc):
        self.name, self.loc, self.energy, self.tool = name, loc, [], None
        self.hits = []      # damage taken, in order, including counters and heals

    def __repr__(self):
        bits = self.energy + ([self.tool] if self.tool else [])
        short = [re.sub(r"^Basic (\w+) Energy$", r"\1", b) for b in bits]
        return f"{self.name}[{', '.join(short)}]" if short else self.name


class Turn:
    def __init__(self, owner, n):
        self.owner, self.n = owner, n
        self.events = []
        self.drew = None
        self.attached = []          # manual attachments from hand
        self.abilities = collections.Counter()
        self.attack = None
        self.hand_at_attack = None  # Prize cards taken after the attack can't be played this turn
        self.flags = []
        self.end_hand = None
        self.end_board = None


class Game:
    def __init__(self, text, pool, me=None):
        self.pool = pool
        self.lines = [l.rstrip("\n") for l in text.splitlines()]
        self.players = []
        for l in self.lines:
            m = re.match(r"^(.+?) drew \d+ cards for the opening hand\.$", l)
            if m and m.group(1) not in self.players:
                self.players.append(m.group(1))
        self.me = me or self._find_me()
        self.opp = next((p for p in self.players if p != self.me), "?")
        self.first = None
        self.hand = collections.Counter()
        self.board = []
        self.turns = []
        self.turn = None
        self.count = collections.Counter()
        self.prizes = collections.Counter()
        self.prize_log = []
        self.random_seen = []       # cards that reached the hand by chance
        self.revealed = set()       # every card of ours the log names
        self.opp_pokemon = []
        self.warnings = []
        self.result = self.how = None
        self.mulligans = collections.Counter()
        self.reshuffled = False
        self.hand_unknown = False   # after your own mulligan, the kept hand never appears
        self.ended_in = None
        self.attackers = collections.defaultdict(collections.Counter)  # "Pokémon: attack" -> attacks, KOs, Prizes
        self.losses = collections.defaultdict(collections.Counter)     # your Pokémon -> KO'd, Prizes given
        self.last_lost = None
        self.last_ability = None    # your Ability on their turn, like Fainting Spell
        self.hand_history = []      # (your turn, hand when the turn's actions ended)
        self._parse()

    def _find_me(self):
        for i, l in enumerate(self.lines):
            m = re.match(r"^(.+?) drew \d+ cards for the opening hand\.$", l)
            if m and i + 2 < len(self.lines) and self.lines[i + 2].strip().startswith("•"):
                return m.group(1)
        return self.players[0] if self.players else "?"

    # ------------------------------------------------------------ helpers
    def _who(self):
        return "(" + "|".join(re.escape(p) for p in self.players) + ")"

    def _bullets(self, i):
        """Card names on the bullet line after line i, and the index after it."""
        out, j = [], i + 1
        while j < len(self.lines) and self.lines[j].strip().startswith("•"):
            body = self.lines[j].strip()[1:].strip()
            out += [c.strip() for c in body.split(",") if c.strip()]
            j += 1
        return out, j

    def _note(self, s):
        if self.turn:
            self.turn.events.append(s)

    def _to_hand(self, cards, random_draw):
        for c in cards:
            self.hand[c] += 1
            self.revealed.add(c)
            if random_draw:
                self.random_seen.append(c)

    def _from_hand(self, c):
        self.revealed.add(c)
        if self.hand[c] > 0:
            self.hand[c] -= 1
            if not self.hand[c]:
                del self.hand[c]
        elif not self.hand_unknown:
            where = f"T{self.turn.n}" if self.turn else "setup"
            self.warnings.append(f"{where}: {c} left the hand but the ledger never saw it arrive")

    def _find(self, name, loc=None, most=True):
        cands = [m for m in self.board if norm(m.name) == norm(name) and (loc is None or m.loc == loc)]
        if not cands and loc is not None:
            cands = [m for m in self.board if norm(m.name) == norm(name)]
        if not cands:
            return None
        return max(cands, key=lambda m: len(m.energy)) if most else cands[0]

    def _active(self):
        return next((m for m in self.board if m.loc == ACTIVE), None)

    def _put(self, name, loc):
        if loc == ACTIVE:
            a = self._active()
            if a:
                a.loc = BENCH
        m = Mon(name, loc)
        self.board.append(m)
        self.revealed.add(name)
        return m

    def _search_or_draw(self, parent_text):
        t = parent_text.lower()
        return "search" if "search" in t else "draw"

    # ------------------------------------------------------------ parsing
    def _parse(self):
        W = self._who()
        me, opp = self.me, self.opp
        parent, parent_text, parent_owner = "", "", None
        parent_is_ability = False
        breakdown_for = None
        i = 0
        while i < len(self.lines):
            raw = self.lines[i]
            line = raw.strip()
            i += 1
            if not line:
                continue
            is_sub = line.startswith("- ")
            body = line[2:] if is_sub else line

            # ----- endings, anywhere
            m = re.search(r"(\S+) wins\.$", line)
            if m and not is_sub:
                self.result = "win" if m.group(1) == me else "loss"
                self.how = line
                self.ended_in = self.turn
                continue
            if line.startswith("•"):
                continue

            if not is_sub:
                parent, parent_text, parent_owner = line, "", None
                parent_is_ability = False
                breakdown_for = None

            # ----- setup
            m = re.match(rf"^{W} decided to go (first|second)\.$", body)
            if m:
                # the decider going first, or the other player going second, puts you first
                self.first = (m.group(1) == me) == (m.group(2) == "first")
                continue
            m = re.match(rf"^{W} drew \d+ cards for the opening hand\.$", body)
            if m:
                if m.group(1) == me:
                    j = i
                    while j < len(self.lines) and not self.lines[j].strip().startswith("•"):
                        j += 1
                    cards, i2 = self._bullets(j - 1)
                    self._to_hand(cards, True)
                    i = i2
                continue
            m = re.match(rf"^{W} took a mulligan\.$", body)
            if m:
                self.mulligans[m.group(1)] += 1
                if m.group(1) == me:
                    # Live lists the hand you sent back as your opening hand and never
                    # prints the seven you kept, so the ledger starts from nothing
                    self.hand.clear()
                    self.random_seen = []
                    self.hand_unknown = True
                continue
            if re.match(r"^Cards revealed from Mulligan", body):
                _, i = self._bullets(i - 1)
                continue
            m = re.match(rf"^{W} drew \d+ more cards? because", body)
            if m:
                parent_text = "draw"
                continue

            # ----- turns
            m = re.match(rf"^{W}'s Turn$", body)
            if m and not is_sub:
                self._close_turn()
                who = m.group(1)
                self.count[who] += 1
                self.turn = Turn(who, self.count[who])
                self.turns.append(self.turn)
                continue
            if body == "Pokémon Checkup":
                continue

            # ----- draws and searches
            m = re.match(rf"^{W} drew a card\.$", body)
            if m:
                continue
            m = re.match(rf"^{W} drew (\d+) cards and played them to the Bench\.$", body)
            if m:
                cards, i = self._bullets(i - 1)
                if m.group(1) == me:
                    for c in cards:
                        self._put(c, BENCH)
                    self._note(f"benched {', '.join(cards)}")
                else:
                    self.opp_pokemon += cards
                    self._note(f"benched {', '.join(cards)}")
                continue
            m = re.match(rf"^{W} drew (.+?) and played it to the Bench\.$", body)
            if m:
                if m.group(1) == me:
                    self._put(m.group(2), BENCH)
                    self._note(f"benched {m.group(2)}")
                else:
                    self.opp_pokemon.append(m.group(2))
                continue
            m = re.match(rf"^{W} drew (\d+) cards\.$", body)
            if m:
                cards, i = self._bullets(i - 1)
                if m.group(1) == me and cards:
                    how = self._search_or_draw(parent_text)
                    self._to_hand(cards, how == "draw")
                    self._note(f"{'searched' if how == 'search' else 'drew'} {', '.join(cards)}")
                continue
            m = re.match(rf"^{W} drew (.+?)\.$", body)
            if m:
                if m.group(1) == me:
                    c = m.group(2)
                    if is_sub:
                        how = self._search_or_draw(parent_text)
                        self._to_hand([c], how == "draw")
                        self._note(f"{'searched' if how == 'search' else 'drew'} {c}")
                    else:
                        self._to_hand([c], True)
                        if self.turn and self.turn.owner == me:
                            self.turn.drew = c
                continue
            m = re.match(rf"^{W} shuffled (\d+) cards into their deck\.$", body)
            if m:
                cards, i = self._bullets(i - 1)
                # Lillie's shuffles the hand; Energy Recycler shuffles the discard pile
                from_hand = "your hand" in parent_text.lower() or "discard pile" not in parent_text.lower()
                if m.group(1) == me and from_hand:
                    self.reshuffled = True
                    for c in cards:
                        self._from_hand(c)
                continue
            # a one-card shuffle-back names the card inline, with no bullet line
            m = re.match(rf"^{W} shuffled (?!their deck)(.+?) into their deck\.$", body)
            if m:
                from_hand = "your hand" in parent_text.lower() or "discard pile" not in parent_text.lower()
                if m.group(1) == me and from_hand:
                    self.reshuffled = True
                    self._from_hand(m.group(2))
                continue
            m = re.match(rf"^{W} moved {W}'s (.+?) to their hand\.$", body)
            if m:
                if m.group(1) == me:
                    self._to_hand([m.group(3)], False)
                continue

            # ----- plays from hand
            m = re.match(rf"^{W} played (.+?) to the (Active Spot|Bench|Stadium spot)\.$", body)
            if m and not is_sub:
                who, c, where = m.groups()
                if who == me:
                    self._from_hand(c)
                    if where == "Stadium spot":
                        self._note(f"stadium {c}")
                    else:
                        self._put(c, ACTIVE if where == "Active Spot" else BENCH)
                        if self.turn:
                            self._note(f"benched {c}")
                elif where != "Stadium spot":
                    self.opp_pokemon.append(c)
                    self._note(f"benched {c}" if where == "Bench" else f"active {c}")
                elif self.turn:
                    self._note(f"stadium {c}")
                parent_owner, parent_text = who, self.pool.text(c)
                continue
            m = re.match(rf"^{W} played (.+?)\.$", body)
            if m and not is_sub:
                who, c = m.groups()
                parent_owner, parent_text = who, self.pool.text(c)
                if who == me:
                    self._from_hand(c)
                self._note(f"played {c}")
                continue
            m = re.match(rf"^{W} attached (.+?) to (.+?) (in the Active Spot|on the Bench)\.$", body)
            if m:
                who, c, tgt, where = m.groups()
                loc = ACTIVE if "Active" in where else BENCH
                if who == me:
                    moving = bool(re.search(r"\bmove\b", parent_text, re.I))
                    if not is_sub:
                        self._from_hand(c)
                        if self.turn:
                            self.turn.attached.append((c, tgt))
                    elif not moving and "from your hand" in parent_text.lower():
                        # Lucky Attachment: an effect that attaches from the hand, on top of
                        # the turn's own attachment
                        self._from_hand(c)
                    mon = self._find(tgt, loc)
                    if mon is None:
                        mon = self._put(tgt, loc)
                        self.warnings.append(f"T{self.turn.n if self.turn else 0}: {tgt} appeared on the board untracked")
                    src_note = ""
                    if is_sub and moving:
                        if re.search(r"from (this|the Attacking) Pok", parent_text):
                            src = self._active()     # Void Gale, Handheld Fan: the attacker
                        else:
                            # Happy Switch, Energy Switch: the log never names the source, so
                            # guess a benched donor before the Active, the fullest one first
                            donors = [x for x in self.board if x is not mon and c in x.energy]
                            donors.sort(key=lambda x: (x.loc == ACTIVE, -len(x.energy)))
                            src = donors[0] if donors else None
                            src_note = f" (from {src.name}, a guess)" if src else " (source unknown)"
                        if src and src is not mon and c in src.energy:
                            src.energy.remove(c)
                    if self.pool.kind(c) == "Tool":
                        mon.tool = c
                    else:
                        mon.energy.append(c)
                    kind = "attached" if not is_sub else ("moved" if moving else "effect-attached")
                    self._note(f"{kind} {c} -> {tgt}{' (active)' if loc == ACTIVE else ''}{src_note}")
                elif not is_sub:
                    self._note(f"attached {c} -> {tgt}")
                continue
            m = re.match(rf"^{W} evolved (.+?) to (.+?) (in the Active Spot|on the Bench)\.$", body)
            if m:
                who, a, b, where = m.groups()
                if who == me:
                    self._from_hand(b)
                    mon = self._find(a, ACTIVE if "Active" in where else BENCH)
                    if mon is None:
                        self.warnings.append(f"T{self.turn.n}: evolved an untracked {a}")
                        mon = self._put(a, ACTIVE if "Active" in where else BENCH)
                    mon.name = b
                    self._note(f"evolved {a} -> {b}")
                else:
                    self.opp_pokemon.append(b)
                    self._note(f"evolved {a} -> {b}")
                continue
            m = re.match(rf"^{W} retreated (.+?) to the Bench\.$", body)
            if m:
                self._note(f"retreated {m.group(2)}")
                continue
            m = re.match(rf"^{W}'s (.+?) is now in the Active Spot\.$", body)
            if m:
                who, name = m.groups()
                if who == me:
                    mon = self._find(name, BENCH)
                    if mon is None:
                        mon = self._find(name) or self._put(name, BENCH)
                    old = self._active()
                    if old and old is not mon:
                        old.loc = BENCH
                    mon.loc = ACTIVE
                continue
            m = re.match(rf"^{W}'s (.+?) was Knocked Out!$", body)
            if m:
                who, name = m.groups()
                if who == me:
                    a = self._active()
                    mon = a if a and norm(a.name) == norm(name) else self._find(name, BENCH, most=False)
                    story = ""
                    if mon:
                        self.board.remove(mon)
                        hp = (self.pool.card(mon.name) or {}).get("hp", "?")
                        parts = " + ".join(str(h) if h >= 0 else f"(healed {-h})" for h in mon.hits)
                        net = sum(mon.hits)
                        took = parts if len(mon.hits) == 1 else f"{parts} = {net}"
                        story = f" (took {took} of {hp} HP" + (f", holding {mon.tool}" if mon.tool else "") + ")"
                    self._note(f"lost {name}{story}")
                    self.losses[name]["KO'd"] += 1
                    self.last_lost = name
                else:
                    self._note(f"knocked out {name}")
                    if self.turn and self.turn.owner == me and self.turn.attack:
                        a = self.turn.attack
                        self.attackers[f"{a['by']}: {a['name']}"]["KOs"] += 1
                self._backfill_prize(name, lost=who == me)
                continue
            m = re.match(rf"^{W} took (a|\d+) Prize cards?\.$", body)
            if m:
                who = m.group(1)
                k = 1 if m.group(2) == "a" else int(m.group(2))
                self.prizes[who] += k
                side = "you" if who == me else "they"
                t = self.turn.n if self.turn else 0
                whose = "You" if self.turn and self.turn.owner == me else "Opp"
                what = self._last_ko(who)
                self.prize_log.append((side, t, k, what, whose))
                if who == me:
                    if self.turn and self.turn.owner == me and self.turn.attack:
                        a = self.turn.attack
                        self.attackers[f"{a['by']}: {a['name']}"]["Prizes"] += k
                    else:  # taken on their turn, by an Ability like Fainting Spell
                        key = self.last_ability or "on their turn"
                        self.attackers[key]["KOs"] += 1
                        self.attackers[key]["Prizes"] += k
                elif what:  # an empty label waits for its KO line, see _backfill_prize
                    self.losses[self.last_lost]["Prizes given"] += k
                continue
            m = re.match(rf"^(.+?) was added to {W}'s hand\.$", body)
            if m:
                c, who = m.groups()
                if who == me and c != "A card":
                    self._to_hand([c], True)
                    self._note(f"prize {c}")
                continue

            # ----- Abilities and attacks
            m = re.match(rf"^{W}'s (.+?) used (.+?)(?: on (.+?)[’']s (.+?) for (\d+) damage)?\.(?: .*)?$", body)
            if m:
                who, poke, name, _tp, tgt, dmg = m.groups()
                parent_owner, parent_text = who, self.pool.text(name)
                is_ability = norm(name) in self.pool.ability_names
                parent_is_ability = is_ability
                if not is_ability:
                    breakdown_for = self.turn
                if who == me:
                    self.revealed.add(poke)
                    if is_ability and self.turn and self.turn.owner != me:
                        self.last_ability = f"{poke}: {name}"
                    if self.turn and self.turn.owner == me:
                        if is_ability:
                            self.turn.abilities[name] += 1
                        else:
                            self.attackers[f"{poke}: {name}"]["attacks"] += 1
                            self.turn.attack = {"by": poke, "name": name, "target": tgt,
                                                "damage": int(dmg) if dmg else None}
                            self.turn.hand_at_attack = sorted(self.hand.elements())
                    self._note(f"{'ability' if is_ability else 'attack'} {poke}: {name}"
                               + (f" -> {tgt} {dmg}" if tgt else ""))
                else:
                    if tgt and dmg and _tp == me:
                        mon = self._find(tgt, ACTIVE)
                        if mon:
                            mon.hits.append(int(dmg))
                    if poke not in self.opp_pokemon:
                        self.opp_pokemon.append(poke)
                    if not is_ability:
                        self._note(f"attack {poke}: {name}" + (f" -> {tgt} {dmg}" if tgt else ""))
                    else:
                        self._note(f"ability {poke}: {name}")
                continue
            m = re.match(rf"^{W} put (\d+) damage counters on .+?[’']s (.+?)\.$", body)
            if m:
                who, k, name = m.group(1), int(m.group(2)), m.group(3)
                if who == me and parent_owner == me and parent_is_ability:
                    mon = self._find(name, BENCH)
                    if mon:
                        mon.hits.append(10 * k)
                elif self.turn and self.turn.attack and self.turn.attack["target"] is None \
                        and who == me and parent_owner == me:
                    self.turn.attack["target"] = name
                    self.turn.attack["counters"] = k
                    self._note(f"  counters {k} -> {name}")
                elif parent_owner == opp and not parent_is_ability:
                    # their attack (Chaotic Pain, Phantom Dive) always lands on your side; in a
                    # mirror the name alone can't say whose Toxel it was
                    mon = self._find(name)
                    if mon:
                        mon.hits.append(10 * k)
                        self._note(f"took {k} counters on {name}")
                elif parent_owner != me:
                    # a Tool or Stadium placed them (Punk Helmet, Risky Ruins); the label names
                    # the wrong player, so trust the board instead
                    mon = self._find(name)
                    if mon and name not in self.opp_pokemon:
                        mon.hits.append(10 * k)
                        self._note(f"took {k} counters on {name}")
                continue
            m = re.match(rf"^{W} moved (\d+) damage counters from .+?[’']s (.+?) to .+?[’']s (.+?)\.$", body)
            if m:
                k, src, dst = int(m.group(2)), m.group(3), m.group(4)
                mon = self._find(dst)
                # Adrena-Brain moves counters onto the other side, so their Ability means yours
                if mon and (parent_owner == opp or (parent_owner != me and dst not in self.opp_pokemon)):
                    mon.hits.append(10 * k)
                    self._note(f"took {k} moved counters on {dst}")
                continue
            m = re.match(rf"^(\d+) damage counters? (?:was|were) placed on {W}[’']s (.+?) for", body)
            if m:
                if m.group(2) == me:
                    mon = self._find(m.group(3), ACTIVE)
                    if mon:
                        mon.hits.append(10 * int(m.group(1)))
                continue
            m = re.match(rf"^{W}[’']s (.+?) took (\d+) damage\.$", body)
            if m:
                if m.group(1) == me:
                    mon = self._find(m.group(2), BENCH)
                    if mon:
                        mon.hits.append(int(m.group(3)))
                continue
            m = re.match(rf"^{W}[’']s (.+?) healed (\d+) damage\.$", body)
            if m:
                if m.group(1) == me:
                    mon = self._find(m.group(2))
                    if mon:
                        mon.hits.append(-int(m.group(3)))
                continue
            if body == "Damage breakdown:":
                parts = []
                j = i
                while j < len(self.lines) and self.lines[j].strip().startswith("•"):
                    parts.append(self.lines[j].strip()[1:].strip())
                    j += 1
                i = j
                if breakdown_for is not None and parts:
                    self._note("  breakdown: " + "; ".join(p for p in parts if not p.startswith("Total")))
                continue
            m = re.match(r"^(.+?) was activated\.$", body)
            if m:
                parent_text = self.pool.text(m.group(1))
                parent_owner = None
                continue
            m = re.match(rf"^(.+?) was discarded from {W}[’']s (.+?)\.$", body)
            if m:
                c, who, name = m.groups()
                if who == me:
                    a = self._active()
                    mon = a if a and norm(a.name) == norm(name) and (c in a.energy or a.tool == c) \
                        else next((x for x in self.board if norm(x.name) == norm(name)
                                   and (c in x.energy or x.tool == c)), None)
                    if mon:
                        if mon.tool == c:
                            mon.tool = None
                        else:
                            mon.energy.remove(c)
                    self._note(f"discarded {c} from {name}")
                continue
            m = re.match(rf"^\d+ cards were discarded from {W}[’']s (.+?)\.$", body)
            if m:
                _, i = self._bullets(i - 1)
                continue
            m = re.match(rf"^{W} discarded (\d+) cards\.$", body)
            if m:
                cards, i = self._bullets(i - 1)
                if m.group(1) == me:
                    for c in cards:
                        self._from_hand(c)
                continue
            m = re.match(rf"^{W} discarded (.+?)\.$", body)
            if m:
                who, c = m.groups()
                # the other player's Stadium play discards the Stadium in play, not a hand card
                if who == me and "Stadium spot" not in parent:
                    self._from_hand(c)
                continue
            # coin flips, statuses, heals, bench damage, shuffles, checkup, ends of turn
        self._close_turn()

    def _last_ko(self, taker=None):
        """The Pokémon behind a Prize: yours when they took it, theirs when you did."""
        if not self.turn:
            return ""
        want = "lost " if taker == self.opp else "knocked out " if taker == self.me else None
        for e in reversed(self.turn.events):
            if e.startswith(("lost ", "knocked out ")) and (want is None or e.startswith(want)):
                return e.split(" ", 2)[-1] if e.startswith("knocked") else e[5:].split(" (took")[0]
        return ""

    def _backfill_prize(self, name, lost):
        """Name a Prize whose line came before its KO line.

        Live prints the Prize first when an effect runs between them, like
        Legacy Energy being discarded from the Pokémon it was on.
        """
        if not self.prize_log or not self.turn:
            return
        side, t, k, what, whose = self.prize_log[-1]
        if what or t != self.turn.n or (side == "they") != lost:
            return
        self.prize_log[-1] = (side, t, k, name, whose)
        if lost:
            self.losses[name]["Prizes given"] += k

    def _close_turn(self):
        t = self.turn
        if not t or t.end_hand is not None:
            return
        t.end_hand = sorted(self.hand.elements())
        t.end_board = [repr(m) for m in sorted(self.board, key=lambda m: m.loc != ACTIVE)]
        if t.owner != self.me:
            return
        self.hand_history.append((t.n, t.hand_at_attack if t.hand_at_attack is not None else t.end_hand))
        if t is self.ended_in and not t.attack:
            t.flags.append("game ended before this turn's attack")
            return
        pool = self.pool
        hand = t.hand_at_attack if t.hand_at_attack is not None else t.end_hand
        # a held Energy
        held = [c for c in hand if pool.kind(c) == "Energy"]
        if not t.attached and held:
            t.flags.append(f"held {held[0]} with no attachment this turn")
        # a Basic kept in hand while the Bench had room; it can't evolve until it has sat a turn
        room = 5 - sum(1 for m in self.board if m.loc == BENCH)
        basics = [c for c in hand if pool.kind(c) == "Pokemon" and pool.stage(c) == 0
                  and "ex" not in norm(c).split()]
        if basics and room > 0:
            t.flags.append(f"held {', '.join(basics)} with {room} Bench space open")
        # a once-per-turn Ability left on the table
        avail = collections.Counter()
        for mon in self.board:
            c = pool.card(mon.name) or {}
            for a in c.get("abilities") or []:
                txt = a.get("text") or ""
                if txt.startswith("Once during your turn") and not txt.startswith("Once during your turn, when"):
                    cap = 1 if "can't use more than 1" in txt else 99
                    avail[a["name"]] = min(cap, avail[a["name"]] + 1)
        for name, k in avail.items():
            used = t.abilities.get(name, 0)
            if used < k:
                t.flags.append(f"{name} used {used} of {k} (check its condition)")
        # no attack, or only a setup attack, while something could have hit
        if self.first and t.n == 1:
            return
        loaded = [f"{m!r} ({', '.join(ready_attacks(pool, m))})" for m in self.board
                  if m.loc == BENCH and ready_attacks(pool, m)]
        a = self._active()
        a_ready = ready_attacks(pool, a) if a else []
        if not t.attack:
            msg = "no attack"
            if a_ready:
                msg += f"; the Active {a!r} could pay for {', '.join(a_ready)}"
            elif a and energy_short(pool, a):
                k, name = energy_short(pool, a)
                msg += f"; the Active {a!r} was {k} Energy short of {name}"
            if loaded:
                msg += f"; loaded on the Bench: {'; '.join(loaded)}"
            t.flags.append(msg)
        elif loaded and not self._hurts(t.attack["name"]):
            t.flags.append(f"setup attack {t.attack['name']} while loaded on the Bench: {'; '.join(loaded)}")

    def stuck(self, min_turns=3):
        """(card, copies, first turn, last turn) for cards that ended min_turns or more
        of your turns in a row in hand without being played."""
        out = []
        cards = {c for _, h in self.hand_history for c in h}
        for c in sorted(cards):
            run = []
            for n, h in self.hand_history + [(None, [])]:
                if c in h:
                    run.append((n, h.count(c)))
                    continue
                if len(run) >= min_turns:
                    out.append((c, min(k for _, k in run), run[0][0], run[-1][0]))
                run = []
        return sorted(out, key=lambda x: (x[2] - x[3], x[0]))

    def _hurts(self, attack):
        c = self.pool.card(self.turn.attack["by"]) if self.turn and self.turn.attack else None
        for a in (c or {}).get("attacks") or []:
            if norm(a["name"]) == norm(attack):
                return hit_size(a) > 0
        return True


# ---------------------------------------------------------------- deck lists
def registered_decks():
    try:
        import decklib
        _, decks = decklib.load()
        return decklib, decks
    except Exception as e:  # the registry is optional for a bare report
        print(f"(deck registry unavailable: {e})", file=sys.stderr)
        return None, []


def deck_list(decklib, source, rev=None):
    if rev:
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{source}"],
                           capture_output=True, text=True)
        text = r.stdout if r.returncode == 0 else ""
    else:
        text = (ROOT / source).read_text(encoding="utf-8")
    return decklib.qty_rows(text)


def match_deck(game, decklib, decks, source=None):
    """(source, rows, unlisted) for the registered deck the log fits best."""
    seen = {norm(c) for c in game.revealed}
    best = None
    for d in decks:
        if source and d["source"] != source:
            continue
        rows = deck_list(decklib, d["source"])
        names = {norm(r[1]) for r in rows}
        if not names:
            continue
        score = len(seen & names) / max(1, len(seen))
        if best is None or score > best[0]:
            best = (score, d["source"], rows, names)
    if not best:
        return None, [], []
    unlisted = sorted({c for c in game.revealed if norm(c) not in best[3]})
    return best[1], best[2], unlisted


def list_commit(decklib, source):
    r = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h", "--", source],
                       capture_output=True, text=True)
    sha = r.stdout.strip()
    if sha and deck_list(decklib, source) != deck_list(decklib, source, sha):
        sha += "+dirty"
    return sha or "uncommitted"


# ---------------------------------------------------------------- luck
def hyper_cdf(k, K, N, n):
    """P(X <= k) drawing n from N with K successes."""
    n = min(n, N)
    tot = math.comb(N, n)
    return sum(math.comb(K, i) * math.comb(N - K, n - i) for i in range(0, min(k, K) + 1)) / tot


def luck_lines(game, rows):
    if not rows:
        return []
    pool = game.pool
    deck = collections.Counter()
    for q, name, _h, _n in rows:
        deck[pool.kind(name)] += q
    N = sum(q for q, *_ in rows)
    n = len(game.random_seen)
    seen = collections.Counter(pool.kind(c) for c in game.random_seen)
    out = [f"{n} cards reached your hand by chance (opening hand, draws, draw effects, Prize cards)"]
    if game.reshuffled:
        out.append("approximate: cards shuffled back into the deck can be drawn twice")
    if game.hand_unknown:
        out.append("undercounted: the hand you kept after your mulligan isn't in the log")
    for kind in ("Supporter", "Energy", "Pokemon", "Item"):
        K = deck.get(kind, 0)
        if not K:
            continue
        k = seen.get(kind, 0)
        exp = n * K / N
        lo = hyper_cdf(k, K, N, n)
        hi = 1 - hyper_cdf(k - 1, K, N, n) if k else 1.0
        tail = f"P(this few or fewer) {lo:.0%}" if k <= exp else f"P(this many or more) {hi:.0%}"
        label = "Pokémon" if kind == "Pokemon" else kind
        line = f"{label}: {k} seen, {exp:.1f} expected from {K} in the deck; {tail}"
        if kind in ("Supporter", "Energy") and k:
            names = collections.Counter(c for c in game.random_seen if pool.kind(c) == kind)
            line += " (" + ", ".join(f"{c} x{v}" if v > 1 else c for c, v in names.items()) + ")"
        out.append(line)
    return out


# ---------------------------------------------------------------- files
def split_header(text):
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            head = {}
            for l in text[4:end].splitlines():
                k, _, v = l.partition(":")
                head[k.strip()] = v.strip()
            return head, text[end + 5:]
    return {}, text


def slug(s):
    s = norm(s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "unknown"


def body_hash(body):
    """Same game, same hash, even after an editor straightens the quotes or drops blank lines."""
    lines = [l.rstrip().replace("\u2019", "'") for l in body.strip().splitlines()]
    return hashlib.sha1("\n".join(l for l in lines if l).encode()).hexdigest()


def cmd_save(a):
    src = Path(a.log).resolve()
    text = src.read_text(encoding="utf-8")
    head, body = split_header(text)
    if head:
        sys.exit(f"{src} already has a header; edit it in place instead")
    LOGS.mkdir(exist_ok=True)
    h = body_hash(body)
    for f in sorted(LOGS.glob("*.txt")):
        if f.resolve() == src:
            continue
        _, b = split_header(f.read_text(encoding="utf-8"))
        if body_hash(b) == h:
            print(f"already archived as {f.relative_to(ROOT)}")
            return
    pool = Pool()
    decklib, decks = registered_decks()
    game = Game(body, pool, a.me)
    source, rows, unlisted = match_deck(game, decklib, decks, a.deck) if decklib else (a.deck, [], [])
    for q, name, hint, num in rows:
        pool.pin(name, hint, num)
    meta = {
        "date": a.date or date.today().isoformat(),
        "player": game.me,
        "deck": source or "?",
        "commit": list_commit(decklib, source) if (decklib and source) else "?",
        "changes": a.changes or "",
        "unlisted": ", ".join(unlisted),
        "mode": a.mode or "",
        "opponent": game.opp,
        "opp_deck": a.opp_deck or "",
        "opp_pokemon": ", ".join(dict.fromkeys(game.opp_pokemon)),
        "went": "first" if game.first else "second" if game.first is not None else "?",
        "result": game.result or "unfinished",
        "how": game.how or "",
        "prizes": f"{game.prizes[game.me]}-{game.prizes[game.opp]}",
        "turns": str(game.count[game.me]),
        "notes": a.notes or "",
    }
    stem = f"{meta['date']}-{Path(meta['deck']).stem if source else 'deck'}-vs-{slug(game.opp)}"
    out = LOGS / f"{stem}.txt"
    k = 2
    while out.exists():
        out = LOGS / f"{stem}-{k}.txt"
        k += 1
    header = "---\n" + "".join(f"{f}: {meta[f]}\n" for f in FIELDS) + "---\n"
    out.write_text(header + body.strip() + "\n", encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")
    print(header, end="")
    try:
        in_logs = src.parent == LOGS.resolve()
    except Exception:
        in_logs = False
    if in_logs and src != out.resolve():
        src.unlink()
        print(f"removed {src.relative_to(ROOT)}; the archived copy replaces it")


def load_game(path, me=None):
    """(header, game, deck rows) for one log, read with the list it was played with."""
    head, body = split_header(Path(path).read_text(encoding="utf-8"))
    pool = Pool()
    decklib, decks = registered_decks()
    source = head.get("deck") if head.get("deck") not in (None, "", "?") else None
    player = head.get("player") or me
    rows = []
    if decklib:
        commit = (head.get("commit") or "").replace("+dirty", "")
        if source and commit and commit not in ("?", "uncommitted"):
            rows = deck_list(decklib, source, commit)
        if not rows:
            source, rows, _ = match_deck(Game(body, pool, player), decklib, decks, source)
    for q, name, hint, num in rows:
        pool.pin(name, hint, num)
    return head, Game(body, pool, player), rows


FLAG_KINDS = [
    ("stranded attacker", r"^no attack; .*loaded on the Bench"),
    ("Active could attack, didn't", r"^no attack; the Active"),
    ("no attack", r"^no attack$"),
    ("setup attack while loaded", r"^setup attack"),
    ("held Energy", r"^held .*Energy with no attachment"),
    ("held Basic", r"^held .* Bench space open"),
    ("unused Ability", r" used \d+ of \d+"),
]


def flag_kind(f):
    return next((k for k, pat in FLAG_KINDS if re.search(pat, f)), "other")


def cmd_report(a):
    path = Path(a.log)
    head, game, rows = load_game(path, a.me)

    me, opp = game.me, game.opp
    print(f"== {path}")
    if head:
        print(" · ".join(f"{k}: {head[k]}" for k in FIELDS if head.get(k)))
    print(f"you: {me} ({'first' if game.first else 'second'}) · opponent: {opp}"
          f" · result: {game.result or 'unfinished'} · prizes {game.prizes[me]}-{game.prizes[opp]}")
    if game.how:
        print(f"ended: {game.how}")
    if game.hand_unknown:
        print("note: you mulliganed, and Live never prints the hand you kept, so the hand lines")
        print("      show only cards the log revealed after that")
    print()
    print("Prize flow")
    for side, t, k, what, whose in game.prize_log:
        print(f"  {whose} T{t}: {side} +{k}  {what}")
    print()
    print("Turn by turn")
    for t in game.turns:
        who = "You" if t.owner == me else "Opp"
        head_l = f"{who} T{t.n}"
        if t.owner == me and t.drew:
            head_l += f"  drew {t.drew}"
        print(head_l)
        for e in t.events:
            print(f"    {e}")
        if t.owner == me:
            print(f"    board: {' | '.join(t.end_board) if t.end_board else '-'}")
            print(f"    hand ({len(t.end_hand)}): {', '.join(t.end_hand) or '-'}")
            for f in t.flags:
                print(f"    ! {f}")
    print()
    print("This game's numbers")
    print("  your attacks:")
    for k, c in sorted(game.attackers.items(), key=lambda kv: -kv[1]["Prizes"]):
        print(f"    {k}: {c['attacks']} attack{'s' if c['attacks'] != 1 else ''}, "
              f"{c['KOs']} KO{'s' if c['KOs'] != 1 else ''}, {c['Prizes']} Prize{'s' if c['Prizes'] != 1 else ''}")
    print("  your losses:")
    for k, c in game.losses.items():
        print(f"    {k}: KO'd {c["KO'd"]}x, gave {c['Prizes given']} Prize{'s' if c['Prizes given'] != 1 else ''}")
    if not game.losses:
        print("    none")
    print("  in hand at the end of 3+ of your turns in a row:")
    for c, k, a_, b_ in game.stuck():
        print(f"    {c}{f' x{k}' if k > 1 else ''}: turns {a_}-{b_}")
    if not game.stuck():
        print("    none")
    print()
    flags = [(t.n, f) for t in game.turns if t.owner == me for f in t.flags]
    print("Flags")
    for n, f in flags:
        print(f"  T{n}: {f}")
    if not flags:
        print("  none")
    print()
    print("Luck")
    for l in luck_lines(game, rows):
        print(f"  {l}")
    if game.warnings:
        print()
        print("Tracking warnings (the hand or board ledger may be off after these)")
        for w in game.warnings:
            print(f"  {w}")


def cmd_summary(a):
    files = sorted(LOGS.glob("*.txt"))
    if not files:
        print("no archived logs")
        return
    groups = collections.defaultdict(collections.Counter)
    opps = collections.defaultdict(collections.Counter)
    flags = collections.defaultdict(collections.Counter)
    games = collections.Counter()
    for f in files:
        head, game, _ = load_game(f)
        if not head:
            print(f"(no header: {f.name}; run save on it)")
            continue
        key = (head.get("deck", "?"), head.get("commit", "?"), head.get("changes") or "as listed")
        res = head.get("result", "?")
        groups[key][res] += 1
        games[key] += 1
        opps[key][f"{head.get('opp_deck') or head.get('opponent')} ({head.get('mode') or 'mode?'}): {res}"] += 1
        for t in game.turns:
            if t.owner == game.me:
                for fl in t.flags:
                    flags[key][flag_kind(fl)] += 1
    for key, c in groups.items():
        deck, commit, changes = key
        other = sum(c.values()) - c["win"] - c["loss"]
        print(f"{deck} @ {commit} ({changes}): {c['win']}-{c['loss']}" + (f", {other} other" if other else "")
              + f" over {games[key]} game{'s' if games[key] != 1 else ''}")
        for k, v in sorted(opps[key].items()):
            print(f"    {k}" + (f" x{v}" if v > 1 else ""))
        if flags[key]:
            print("    flags per game: " + ", ".join(
                f"{k} {v / games[key]:.1f}" for k, v in flags[key].most_common()))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("log")
    s.add_argument("--deck", help="deck source, e.g. dark-gang.md; matched from the log when left out")
    s.add_argument("--mode", choices=["ranked", "casual", "league", "home", "friendly"])
    s.add_argument("--changes", help="how the list played differs from the committed one")
    s.add_argument("--opp-deck", help="the opponent's archetype")
    s.add_argument("--date", help="YYYY-MM-DD; today when left out")
    s.add_argument("--notes")
    s.add_argument("--me", help="your Live name, when it can't be read from the opening hand")
    r = sub.add_parser("report")
    r.add_argument("log")
    r.add_argument("--me")
    sub.add_parser("summary")
    a = p.parse_args()
    {"save": cmd_save, "report": cmd_report, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    main()
