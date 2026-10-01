#!/usr/bin/env python3
"""Build calc.html, the damage calculator for Lucky Haunt, and its data file.

    python3 build_calc.py            # the page and assets/calc/pool.json
    python3 build_calc.py --review   # also print how every card text was read

The page is a form: pick the opponent's Pokémon, say what is on it, and each
of the deck's five attackers shows what it does. Everything the form needs to
know about a card is worked out here, ahead of time, so the script on the page
does arithmetic and nothing else.

Three sources:

    legal-cards-<epoch>.json   the newest snapshot from fetch_legal_pool.py.
                               Every Standard-legal Pokémon is a possible
                               target. No network: the build stays offline and
                               --check stays honest.
    cards.csv + dark-lucky.md  the attackers. The deck list pins the printing
                               and cards.csv carries its text, so the numbers on
                               the page are the numbers on the card.
    calc.toml                  the hand-written callouts, what to do about a
                               card rather than what it does.

The part that matters is reading card text into effects. An Ability that
says "takes 30 less damage" becomes {"k": "reduce", "n": 30}, a "prevent all
damage ... from Pokémon ex" becomes a prevent gated on the attacker being an
ex, and so on. The patterns cover everything in the pool that touches the
math; a sentence that sounds like it should and matched nothing is printed,
so a new card's wording turns up as a line in the build rather than as a
wrong number at the table. Tools, Stadiums, and Special Energy are few and
named, so those are written out by hand below instead of parsed.

The condition tokens an effect carries ("atk:ex", "tgt:bench", "dmg:>=200")
are read by calc.js's test(). A new token needs a case there too.
"""
import glob, hashlib, json, re, sys, tomllib
from pathlib import Path

from decklib import qty_rows
from pokelib import CREDITS_NOTE, COST_TYPE, esc, find_card, page

ROOT = Path(__file__).parent
DEST = ROOT / "calc.html"
OUT = ROOT / "assets" / "calc"
POOL = OUT / "pool.json"
NOTES = ROOT / "calc.toml"
DECK = "dark-lucky.md"
DECK_PAGE = "dark-lucky.html"
TITLE = "Damage Calculator"
MASCOT = ["pokedex", "gengar-hop"]
REVIEW = "--review" in sys.argv

# The five that attack, in the order the row shows them, and the one attack
# each is here for. Okidogi ex's other attack is Poisonous Musculature, which
# does no damage; what it leaves behind is the Poisoned switch on the dog's row.
ATTACKERS = [
    ("gengar", "Gengar ex", "Chaotic Pain"),
    ("mega", "Mega Gengar ex", "Void Gale"),
    ("okidogi", "Okidogi ex", "Chain-Crazed"),
    ("blissey", "Blissey ex", "Return"),
    ("toxtricity", "Toxtricity", "Gentle Slap"),
]

TYPES = ["Grass", "Fire", "Water", "Lightning", "Psychic", "Fighting",
         "Darkness", "Metal", "Dragon", "Fairy", "Colorless"]


def fx(k, *cond, **kw):
    """One effect. cond is the tokens that all have to hold for it to apply."""
    out = {"k": k, **kw}
    if cond:
        out["if"] = list(cond)
    return out


def info(text, tone="bad", *cond):
    return fx("info", *cond, text=text, tone=tone)


# --- the named cards -------------------------------------------------------
# Written out by hand: there are few of them, and each is a card a person
# picks from a list, so a wrong reading would be easy to spot and expensive
# to miss. An empty list means it does nothing to this deck's attacks; those
# go in the menu's second group so the menu is still the full set.

TOOLS = {
    "Hero's Cape": [fx("hp", n=100)],
    "Cynthia's Power Weight": [fx("hp", "tgt:owner=Cynthia's", n=70)],
    "Ancient Booster Energy Capsule": [fx("hp", "tgt:ancient", n=60)],
    "Colbur Berry": [fx("reduce", "atk:type=Darkness", n=60, once=True)],
    "Sacred Charm": [fx("reduce", "atk:ability", n=30)],
    "Survival Brace": [fx("survive")],
    "Deluxe Bomb": [fx("retaliate", "tgt:active", n=12)],
    # the holder isn't a Mega, and the hit is 240 or more from a Mega
    # Evolution Pokémon ex: a Void Gale into Weakness, never a plain one
    "Tremendous Bomb": [fx("retaliate", "tgt:active", "tgt:!mega", "atk:mega",
                           "dmg:>=240", n=12)],
    "Punk Helmet": [fx("retaliate", "tgt:active", "tgt:type=Darkness", n=4)],
    "Lillie's Pearl": [fx("prize", "tgt:owner=Lillie's", n=-1)],
    "Team Rocket's Hypnotizer": [info(
        "Whatever damages it falls Asleep, while it is an Active Team "
        "Rocket's Pokémon.", "bad", "tgt:active", "tgt:owner=Team Rocket's")],
    "Handheld Fan": [info(
        "Whatever damages it while it is Active moves an Energy to your "
        "Bench.", "bad", "tgt:active")],
}

STADIUMS = {
    "Gravity Mountain": [
        fx("hp", "tgt:stage=Stage 2", n=-30),
        info("Your Stage 2s lose 30 HP too: Gengar ex is 250 and the Mega "
             "320.", "bad")],
    "Lively Stadium": [fx("hp", "tgt:basic", n=30)],
    "Ange Floette": [fx("hp", "tgt:name=Mega Floette ex", n=150)],
    "Full Metal Lab": [fx("reduce", "tgt:type=Metal", n=30)],
    "Granite Cave": [fx("reduce", "tgt:owner=Steven's", n=30)],
    # counters placed on the Bench by an attack's effect, which is Pain
    "Battle Cage": [fx("prevent", "tgt:bench", what="effects")],
    "Neutralization Zone": [fx("prevent", "tgt:!rulebox", "atk:ex",
                               what="damage")],
    "Festival Grounds": [fx("noPoison")],
    "Team Rocket's Watchtower": [
        fx("noAbilities", who="Colorless"),
        info("Blissey ex has no *Happy Switch*.", "bad")],
    "Jamming Tower": [fx("noTools")],
}

ENERGIES = {
    "Mist Energy": [fx("prevent", what="effects")],
    "Rocky Fighting Energy": [fx("prevent", "tgt:type=Fighting",
                                 what="effects")],
    "Growing Grass Energy": [fx("hp", "tgt:type=Grass", n=20)],
    "Legacy Energy": [fx("prize", n=-1)],
    "Spiky Energy": [fx("retaliate", "tgt:active", n=2)],
}


# --- reading card text -----------------------------------------------------
# Abilities and Rules apply to the card that carries them. An attack's
# "during your opponent's next turn" applies once, the turn after they use it,
# which is what the Last attack used menu is for.

# who a clause is about. Longest first, so "Basic Pokémon ex" is read before
# "Pokémon ex" can claim half of it, and each phrase is cut out once matched.
ATTACKER_WORDS = [
    ("Basic non-Colorless Pokémon", ["atk:basic", "atk:!colorless"]),
    ("Mega Evolution Pokémon ex", ["atk:mega"]),
    ("Basic Pokémon ex", ["atk:basic", "atk:ex"]),
    ("Basic Pokémon", ["atk:basic"]),
    ("Evolution Pokémon", ["atk:evolution"]),
    ("Tera Pokémon", ["atk:tera"]),
    ("Burned Pokémon", ["atk:burned"]),
    ("Ancient Pokémon", ["atk:ancient"]),
    ("Future Pokémon", ["atk:future"]),
    ("Pokémon that have an Ability", ["atk:ability"]),
    ("Pokémon ex", ["atk:ex"]),
]
TYPE_RUN = re.compile(r"((?:%s)(?:(?:, or |, | or )(?:%s))*) Pokémon"
                      % ("|".join(TYPES), "|".join(TYPES)))

# Abilities that say something about a card other than the one carrying them,
# or about the game rather than the damage. Read by hand. A board-wide shield
# that covers its own carrier too carries the effect as well as the callout.
BY_HAND = {
    "Spherical Shield": [fx("prevent", "tgt:bench", what="all")],
    "Protective Bell": [
        fx("reduce", n=10),
        info("Every one of their Pokémon takes 10 less damage, this one "
             "included.")],
    "Protective Armor": [
        fx("reduce", "tgt:active", n=10),
        info("While it is Active, every one of their Pokémon takes 10 less "
             "damage.")],
    "Repelling Veil": [fx("prevent", "tgt:basic",
                          "tgt:owner=Team Rocket's", what="effects")],
    "Primal Root": [fx("cost", "tgt:active", "atk:basic", n=1)],
    "Ancient Bulwark": [info(
        "While it is on their Bench, an attacker of yours holding 2 or fewer "
        "Energy does no damage to any of their Pokémon.")],
    "Gear Coating": [info(
        "Their Pokémon holding Metal Energy take 20 less damage.")],
    "Tundra Wall": [info(
        "Their Pokémon holding Water Energy take 50 less damage.")],
    "Stone Palace": [info(
        "While it is on their Bench, their Steven's Pokémon take 30 less "
        "damage.")],
    "Curly Wall": [info(
        "With two Bouffalant in play, their Basic Colorless Pokémon take 60 "
        "less damage.")],
    "Flower Curtain": [info(
        "Their Benched Pokémon with no Rule Box take no damage from "
        "attacks.", "bad")],
    "Mighty Shell": [info(
        "Nothing holding Special Energy can touch it, *Chaotic Pain* "
        "included: a Gengar ex paid by Neo Upper is shut out.")],
    # these three switch off your Abilities rather than touch the damage,
    # and calc.toml's note on each says it in the deck's own terms
    "Midnight Fluttering": [],
    "Initialization": [],
    "Sticky Bind": [],
    "Wide Wall": [info(
        "While it is Active, your Supporters do nothing to their Pokémon, "
        "Boss's Orders included.", "bad", "tgt:active")],
    "Snow Camouflage": [info("Boss's Orders can't drag it up.")],
    "Unnerve": [info("Boss's Orders can't drag it up.")],
    "Protective Sail": [info("Boss's Orders can't drag it up.")],
    # HP that hangs on something the form doesn't ask: the Energy's type,
    # or how many Prizes you have taken. Callouts, with the number to add.
    "Adrena-Power": [info("Holding Darkness Energy, it has 100 more HP.")],
    "Scale Up": [info("Holding 6 or more Grass Energy, it has 250 more HP.")],
    "Resilient Soul": [info("It has 50 more HP for each Prize you have "
                            "taken.")],
    "Craftsmanship": [info("It has 40 more HP for each Fighting Energy on "
                           "it.")],
    "Tyrannically Gutsy": [fx("hp", "tgt:special", n=150)],
    "Vibrant Dance": [
        fx("hp", n=40),
        info("Every one of their Pokémon has 40 more HP, this one included.")],
    "Adrena-Pheromone": [fx("coin", text=(
        "Holding Darkness Energy, it flips a coin when an attack damages it, "
        "and heads prevents the damage."))],
}

# Abilities that read like defence and do nothing to these attackers. Listed
# so --review shows them as read rather than missed.
IGNORED = {
    "Gloomy Garbage",   # your attacker holds a Tool, which this deck never does
    "Azure Seas",       # their own attacks
    "Luminous Wing",    # Abilities only; Surge targets your own Pokémon
    "Sparkling Scales", # Tera attackers only
    "Thick Fat",        # Fire and Water only
    "Fairy Zone",       # their Dragon-weak cards, and you have no Dragon
    "Supereffective Pheromones",  # Weakness x3, and nothing of yours is
                                  # weak to Illumise or Volbeat
}

# a sentence that looks like it should have matched one of the patterns
# a sentence that looks like it should have matched one of the patterns.
# "do 30 more damage" is their offence and never is; "takes 30 more" is.
SUSPECT = re.compile(r"less damage|takes \d+ more damage|prevent|effects of|"
                     r"Weakness|no Abilities|damage counters on the Attacking|"
                     r"Defending Pokémon|\+\d+ HP", re.I)


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def sentences(t):
    """Split on full stops, keeping "(Damage is not an effect.)" attached."""
    t = re.sub(r"\s*\([^)]*\)", "", norm(t))
    return [s.strip() for s in re.split(r"(?<=\.)\s+", t) if s.strip()]


def who(clause):
    """The attacker tokens a clause names."""
    toks = []
    for phrase, t in ATTACKER_WORDS:
        if phrase in clause:
            toks += t
            clause = clause.replace(phrase, "")
    m = TYPE_RUN.search(clause)
    if m:
        toks.append("atk:type=" + "|".join(re.findall("|".join(TYPES),
                                                       m.group(1))))
    return toks


def threshold(s):
    m = re.search(r"if that damage is (\d+) or (more|less)", s)
    if not m:
        return []
    return [f"dmg:{'>=' if m.group(2) == 'more' else '<='}{m.group(1)}"]


def bare(s):
    """A next-turn sentence without its timing, which the menu already says."""
    s = re.sub(r"^(?:If heads, )?(?:during your opponent's next turn, )",
               "", s, flags=re.I)
    return s[0].upper() + s[1:]


def read_sentence(s, next_turn=False):
    """[effects] for one sentence, or None if nothing matched.

    next_turn means the sentence came from an attack's "during your
    opponent's next turn", where "the Defending Pokémon" is whichever of
    your Pokémon was Active when it hit.
    """
    s = bare(s)

    m = re.search(r"this Pokémon takes (\d+) less damage from attacks(.*)", s,
                  re.I)
    if m:
        return [fx("reduce", *who(m.group(2)), n=int(m.group(1)))]
    m = re.search(r"If this Pokémon has any Energy attached, it takes (\d+) "
                  r"less damage", s)
    if m:
        return [fx("reduce", "tgt:energy", n=int(m.group(1)))]
    m = re.search(r"this Pokémon takes (\d+) more damage", s, re.I)
    if m:
        return [fx("more", n=int(m.group(1)))]

    if re.search(r"prevent all .*attacks", s, re.I) and "this Pokémon" in s:
        if "Special Energy attached" in s:
            return None   # who holds Special Energy is not on the form
        what = ("all" if "damage from and effects of" in s
                else "effects" if re.search(r"prevent all effects of", s, re.I)
                else "damage")
        cond = (["tgt:bench"] if "on your Bench" in s else []) \
            + who(s) + threshold(s)
        return [fx("prevent", *cond, what=what)]

    m = re.search(r"As long as this Pokémon is in the Active Spot, attacks "
                  r"used by your opponent's Active Pokémon do (\d+) less", s)
    if m:
        return [fx("debuff", "tgt:active", n=int(m.group(1)))]
    m = re.search(r"(?:place|put) (\d+) damage counters on the Attacking", s)
    if m:
        cond = ["tgt:active"] if "Active Spot" in s else []
        return [fx("retaliate", *cond, n=int(m.group(1)))]
    if re.search(r"put damage counters on the Attacking Pokémon equal to", s):
        return [fx("retaliate", n="equal")]
    if re.search(r"this Pokémon has no Weakness", s, re.I):
        return [fx("noWeak")]

    if next_turn:
        m = re.search(r"attacks used by the Defending Pokémon do (\d+) less",
                      s, re.I)
        if m:
            return [fx("debuff", n=int(m.group(1)), defending=True)]
        if re.search(r"If the Defending Pokémon is a Basic Pokémon, it can't "
                     r"attack", s):
            return [fx("cantAttack", "atk:basic", defending=True)]
        if re.search(r"the Defending Pokémon can't (?:use )?attack", s, re.I):
            return [fx("cantAttack", defending=True)]
        if re.search(r"attacks used by the Defending Pokémon cost Colorless "
                     r"more", s, re.I):
            return [fx("cost", n=1, defending=True),
                    info("Its Retreat Cost is [C] more too.")]
    return None


def coin_ability(t):
    if re.search(r"is damaged by an attack, flip a coin\. If heads, prevent "
                 r"that damage|damage is done to this Pokémon by attacks, flip "
                 r"a coin\. If heads, prevent that damage", norm(t)):
        return [fx("coin", text="It flips a coin on every hit, and heads "
                                "prevents the damage.")]
    return None


misses = []   # (card, source, sentence) that looked relevant and matched nothing


def read_ability(card, a):
    name, text = a["name"], a.get("text") or ""
    if name in BY_HAND:
        return BY_HAND[name]
    if name in IGNORED:
        return []
    got = coin_ability(text)
    if got:
        return got
    out = []
    for s in sentences(text):
        r = read_sentence(s)
        if r:
            out += r
        elif SUSPECT.search(s):
            misses.append((card["name"], name, s))
    return out


def read_attack(card, atk):
    """(label suffix, effects) for an attack that leaves something behind for
    your next turn, or None for one that doesn't."""
    text = norm(atk.get("text"))
    if "opponent's next turn" not in text:
        return None
    if "Flip a coin" in text:
        when = "heads"
    elif "Knocked Out by damage from this attack" in text:
        when = "after a KO"
    else:
        when = ""
    out = []
    for s in sentences(text):
        if "opponent's next turn" not in s:
            continue
        r = read_sentence(s, next_turn=True)
        if r is None:
            # anything else that lasts into your turn is still worth seeing:
            # no Items, can't retreat, a Pokémon discarded at the end of it
            r = [info(bare(s))]
            if REVIEW:
                misses.append((card["name"], atk["name"], s))
        out += r
    return when, out


# --- the pool --------------------------------------------------------------

def newest_snapshot():
    files = sorted(glob.glob(str(ROOT / "legal-cards-*.json")),
                   key=lambda p: int(re.search(r"(\d+)\.json$", p).group(1)))
    if not files:
        raise SystemExit("no legal-cards-*.json; run fetch_legal_pool.py")
    return Path(files[-1])


def owner(name):
    m = re.match(r"((?:Team Rocket|[A-Z][\w.]*)'s) ", name)
    return m.group(1) if m else ""


def stage(c):
    sub = c.get("subtypes") or []
    for s in ("Basic", "Stage 1", "Stage 2"):
        if s in sub:
            return s
    # one Mega in the pool carries no stage; what it grows from says which
    return "Stage 1" if c.get("evolvesFrom") else "Basic"


def is_regular(c):
    """A main-set print, not a secret rare numbered past the set's total."""
    n = re.match(r"\d+", c["number"] or "")
    return bool(n) and int(n.group()) <= (c["set"].get("printedTotal") or 999)


def key(c):
    """What makes two prints the same card to an attacker."""
    return json.dumps([c["name"], c.get("hp"), c.get("types"),
                       c.get("abilities"), c.get("attacks"),
                       c.get("weaknesses"), c.get("resistances")],
                      sort_keys=True, ensure_ascii=False)


def load_pool(snap):
    data = json.loads(snap.read_text(encoding="utf-8"))
    raw = [c for c in data["cards"] if c["supertype"] == "Pokemon"
           or (c["supertype"] == "Trainer" and c.get("hp"))]   # the Fossils

    # one entry per distinct card. the regular print, from the newest set,
    # stands in for its reprints and secret rares; it is only the picture.
    best = {}
    for c in raw:
        k = key(c)
        rank = (is_regular(c), c["set"].get("releaseDate", ""))
        if k not in best or rank > best[k][0]:
            best[k] = (rank, c)
    chosen = [c for _, c in best.values()]

    # what each name grows into, for "Pain it before it evolves"
    kids = {}
    for c in raw:
        if c.get("evolvesFrom"):
            kids.setdefault(c["evolvesFrom"], set()).add(c["name"])

    def grows(name):
        seen, todo = set(), [name]
        while todo:
            for k in kids.get(todo.pop(), ()):
                if k not in seen:
                    seen.add(k)
                    todo.append(k)
        return sorted(n for n in seen if n.endswith(" ex"))

    cards = []
    for c in chosen:
        sub = c.get("subtypes") or []
        fossil = c["supertype"] == "Trainer"
        rules = " ".join(c.get("rules") or [])
        tags = [t for t, hit in (
            ("ex", "ex" in sub), ("mega", "MEGA" in sub),
            ("tera", "Tera" in sub), ("ancient", "Ancient" in sub),
            ("future", "Future" in sub), ("fossil", fossil)) if hit]
        card = {
            "id": c["id"],
            "name": c["name"],
            "set": c["set"].get("ptcgoCode") or c["set"]["id"].upper(),
            "no": c["number"],
            "hp": int(c.get("hp") or 0),
            "types": c.get("types") or ["Colorless"],
            "stage": "Basic" if fossil else stage(c),
            "tags": tags,
            "prizes": 3 if "Mega Evolution ex Rule" in rules
            else 2 if "ex" in sub else 1,
        }
        if owner(c["name"]):
            card["owner"] = owner(c["name"])
        if c.get("weaknesses"):
            card["weak"] = [w["type"] for w in c["weaknesses"]]
        # upstream has typos here (a Murkrow "resists" Fighting ×2), so a
        # value that isn't a subtraction is reported and left off rather
        # than guessed at
        resist = []
        for r in c.get("resistances") or []:
            if re.fullmatch(r"-\d+", r["value"]):
                resist.append([r["type"], -int(r["value"])])
            else:
                print(f"build_calc: {c['name']} {c['set']['name']} "
                      f"{c['number']} has Resistance {r['type']} "
                      f"{r['value']!r}, left off", file=sys.stderr)
        if resist:
            card["resist"] = resist
        if c.get("evolvesFrom"):
            card["from"] = c["evolvesFrom"]
        into = grows(c["name"])
        if into:
            card["into"] = into
        # an attack that deals damage, for whether Concealment matters here
        card["hits"] = any(re.match(r"\d", a.get("damage") or "")
                           for a in c.get("attacks") or [])

        abilities = []
        for a in c.get("abilities") or []:
            effects = read_ability(c, a)
            abilities.append({"name": a["name"], "text": norm(a["text"]),
                              **({"fx": effects} if effects else {})})
        if abilities:
            card["abilities"] = abilities
        moves = []
        for a in c.get("attacks") or []:
            got = read_attack(c, a)
            if got and got[1]:
                when, effects = got
                moves.append({"name": a["name"], "text": norm(a.get("text")),
                              **({"when": when} if when else {}),
                              "fx": effects})
        if moves:
            card["next"] = moves
        card["_attacks"] = [a["name"] for a in c.get("attacks") or []]
        cards.append(card)

    cards.sort(key=lambda c: (c["name"], c["set"], c["no"]))
    trainers = {c["name"]: norm(" ".join(c.get("rules") or []))
                for c in data["cards"] if c["supertype"] in ("Trainer", "Energy")}
    return data, cards, trainers


# --- the attackers ---------------------------------------------------------

ATTACK = re.compile(r"^\[(\w*)\] (.+?)(?: \((\d+)\+?\))?(?: - (.*))?$")


def attackers():
    """The five, read off the deck list and cards.csv, never typed in here."""
    deck = qty_rows((ROOT / DECK).read_text(encoding="utf-8"))
    out = []
    for slug, name, move in ATTACKERS:
        row = next((r for r in deck if r[1] == name), None)
        if not row:
            raise SystemExit(f"build_calc: {name} is not in {DECK}'s deck list")
        card = find_card(name, row[2], row[3])
        if not card:
            raise SystemExit(f"build_calc: {name} {row[2]} {row[3]} is not "
                             "in cards.csv")
        hit = None
        for k in ("attack1", "attack2", "attack3", "attack4"):
            m = ATTACK.match(card.get(k) or "")
            if m and m.group(2) == move:
                hit = m
        if not hit:
            raise SystemExit(f"build_calc: {name} has no attack named {move}")
        cost, _, dmg, text = hit.groups()
        a = {
            "key": slug,
            "name": name,
            "move": move,
            "cost": [COST_TYPE[ch] for ch in cost],
            "text": text or "",
            "type": card["card_type"],
            "stage": card["stage"],
            "hp": int(card["hp"]),
            "weak": card["weakness"].split(" ")[0],
            "ex": name.endswith(" ex"),
            "mega": name.startswith("Mega "),
            "ability": bool(card["card_text"]),
            "icon": f"./assets/calc/{slug}.png",
        }
        counters = re.search(r"Place (\d+) damage counters on 1 of your "
                             r"opponent's Pokémon", text or "")
        if counters:
            a["counters"] = int(counters.group(1))
        elif dmg:
            a["damage"] = int(dmg)
        else:
            raise SystemExit(f"build_calc: can't read the damage of {move}")
        poison = re.search(r"If this Pokémon is Poisoned, this attack does "
                           r"(\d+) more damage", text or "")
        if poison:
            a["poison"] = int(poison.group(1))
        out.append(a)
    return out


# --- the hand-written notes ------------------------------------------------

def italics(s):
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", esc(s))


def read_notes(cards, trainers):
    """[note html], and {name: [note index]} for every card, Ability, and
    attack name a note hangs on."""
    names = {c["name"] for c in cards} | set(trainers)
    abilities = {a["name"] for c in cards for a in c.get("abilities", [])}
    attacks = {a for c in cards for a in c["_attacks"]}
    notes, hooks = [], {"cards": {}, "abilities": {}, "attacks": {}}
    data = tomllib.loads(NOTES.read_text(encoding="utf-8"))
    for i, n in enumerate(data.get("note", [])):
        if n.get("tone") not in ("good", "bad"):
            raise SystemExit(f"calc.toml note {i + 1}: tone is good or bad")
        html = italics(n["text"])
        if n.get("link"):
            html += (f' <a href="./{DECK_PAGE}#{esc(n["link"])}">'
                     "Why</a>")
        notes.append({"tone": n["tone"], "html": html})
        for kind, known in (("cards", names), ("abilities", abilities),
                            ("attacks", attacks)):
            for name in n.get(kind, []):
                if name not in known:
                    print(f"calc.toml: no legal card has the {kind[:-1]} "
                          f"{name!r}, skipped", file=sys.stderr)
                    continue
                hooks[kind].setdefault(name, []).append(len(notes) - 1)
    return notes, hooks


# --- the page --------------------------------------------------------------

def options(table, trainers, blank):
    """<option>s, the ones that change the math first, then the rest."""
    def opt(n):
        return f'<option value="{esc(n)}">{esc(n)}</option>'
    live = sorted(n for n in trainers if table.get(n))
    rest = sorted(n for n in trainers if n not in live)
    out = [f'<option value="">{esc(blank)}</option>']
    out.append('<optgroup label="Changes the math">'
               + "".join(map(opt, live)) + "</optgroup>")
    if rest:
        out.append('<optgroup label="Nothing to your attacks">'
                   + "".join(map(opt, rest)) + "</optgroup>")
    return "".join(out)


def body(atk, tools, stadiums, specials, pool_url):
    picks = "\n".join(
        f'\t\t\t\t\t<label><input type="radio" name="attacker" '
        f'value="{a["key"]}"{" checked" if i == 0 else ""} />'
        f'<img src="{a["icon"]}" alt="{esc(a["name"])}" width="386" '
        f'height="266" /><output data-badge="{a["key"]}"></output></label>'
        for i, a in enumerate(atk))
    # the answer leads, then the form that asks the question
    return f"""\t\t\t<section data-attacker aria-labelledby="attacker">
				<h2 id="attacker">Attacker</h2>
				<fieldset data-picks>
					<legend>Who attacks</legend>
{picks}
				</fieldset>
				<table data-moves>
					<thead>
						<tr><th>Attack</th><th>Cost</th><th>Damage</th></tr>
					</thead>
					<tbody></tbody>
				</table>
				<div data-notes></div>
			</section>
			<section data-opponent data-pool="{pool_url}" aria-labelledby="opponent">
				<h2 id="opponent">Opponent</h2>
				<div data-search>
					<label for="q">Their Pokémon</label>
					<div data-box>
						<input id="q" type="search" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="hits" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" enterkeyhint="search" placeholder="Search every legal Pokémon" />
						<button type="button" data-clear hidden>Clear</button>
					</div>
					<ul id="hits" role="listbox" aria-label="Matching Pokémon" hidden></ul>
				</div>
				<div data-row>
					<div data-fields>
						<fieldset data-energy>
							<legend>Energy <output id="energy-total">0</output></legend>
							<div data-stepper>
								<span>Basic</span>
								<button type="button" data-step="basic" data-by="-1" aria-label="One less Basic Energy">−</button>
								<output id="basic">0</output>
								<button type="button" data-step="basic" data-by="1" aria-label="One more Basic Energy">+</button>
							</div>
							<select id="special" aria-label="Add a Special Energy">{specials}</select>
							<ul data-chips></ul>
						</fieldset>
						<fieldset data-position>
							<legend>Position</legend>
							<label><input type="radio" name="position" value="active" checked /> Active</label>
							<label><input type="radio" name="position" value="bench" /> Bench</label>
						</fieldset>
						<label data-field><span>Damage on it</span>
							<span data-stepper>
								<button type="button" data-step="damage" data-by="-10" aria-label="10 less damage">−</button>
								<input id="damage" type="number" inputmode="numeric" min="0" step="10" value="0" />
								<button type="button" data-step="damage" data-by="10" aria-label="10 more damage">+</button>
							</span>
						</label>
						<label data-field><span>Tool</span> <select id="tool">{tools}</select></label>
						<label data-field data-last hidden><span>Last attack used</span> <select id="last"></select></label>
						<label data-field><span>Stadium in play</span> <select id="stadium">{stadiums}</select></label>
					</div>
					<figure data-preview>
						<a data-art target="_blank" rel="noopener"><img src="./assets/calc/card-back.png" alt="" width="365" height="512" /></a>
						<figcaption>Pick a Pokémon</figcaption>
					</figure>
				</div>
				<ul data-callouts></ul>
			</section>"""


def stamp(path):
    """?v= from the file's own bytes, so a phone never runs new HTML against
    a cached old script, and an unchanged file keeps its URL."""
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


def main():
    snap = newest_snapshot()
    data, cards, trainers = load_pool(snap)
    atk = attackers()
    notes, hooks = read_notes(cards, trainers)

    named = {}
    for label, table in (("Tool", TOOLS), ("Stadium", STADIUMS),
                         ("Special Energy", ENERGIES)):
        for name in table:
            if name not in trainers:
                print(f"build_calc: the {label} {name!r} is no longer in the "
                      "legal pool", file=sys.stderr)

    def kind(sub):
        return sorted(c["name"] for c in data["cards"]
                      if sub in (c.get("subtypes") or [])
                      and c["supertype"] in ("Trainer", "Energy"))

    tool_names = sorted(set(kind("Pokémon Tool")))
    stadium_names = sorted(set(kind("Stadium")))
    special_names = sorted({c["name"] for c in data["cards"]
                            if c["supertype"] == "Energy"
                            and "Special" in (c.get("subtypes") or [])})
    for names, table in ((tool_names, TOOLS), (stadium_names, STADIUMS),
                         (special_names, ENERGIES)):
        for n in names:
            named[n] = {"text": trainers.get(n, ""),
                        "fx": table.get(n, []),
                        **({"notes": hooks["cards"][n]}
                           if n in hooks["cards"] else {})}

    for c in cards:
        ids = list(hooks["cards"].get(c["name"], []))
        for a in c.get("abilities", []):
            ids += hooks["abilities"].get(a["name"], [])
        for a in c.pop("_attacks"):
            ids += hooks["attacks"].get(a, [])
        if ids:
            c["notes"] = sorted(set(ids))

    OUT.mkdir(parents=True, exist_ok=True)
    head = json.dumps({
        "snapshot": snap.name,
        "fetched": data["fetched_utc"],
        "attackers": atk,
        "named": named,
        "notes": notes,
    }, ensure_ascii=False, separators=(",", ":"))
    # one card per line, so a new snapshot reads as a diff of the cards it
    # changed rather than one line that changed
    lines = ",\n".join(json.dumps(c, ensure_ascii=False, separators=(",", ":"))
                       for c in cards)
    POOL.write_text(head[:-1] + ',"cards":[\n' + lines + "\n]}\n",
                    encoding="utf-8")

    pool_url = f"./assets/calc/pool.json?v={stamp(POOL)}"
    css = OUT / "calc.css"
    js = OUT / "calc.js"
    subtitle = f'For the <a href="./{DECK_PAGE}">Lucky Haunt</a> deck'
    out = page(DEST, TITLE, subtitle, "",
               body(atk, options(TOOLS, tool_names, "No Tool"),
                    options(STADIUMS, stadium_names, "No Stadium"),
                    options(ENERGIES, special_names, "+ Special Energy"),
                    pool_url),
               CREDITS_NOTE, MASCOT,
               script=f"./assets/calc/calc.js?v={stamp(js)}",
               head=(f'<link rel="stylesheet" '
                     f'href="./assets/calc/calc.css?v={stamp(css)}" />'))

    with_fx = sum(1 for c in cards if any("fx" in a for a in c.get("abilities", []))
                  or c.get("next"))
    print(f"calc.html: {len(cards)} Pokémon, {with_fx} with effects, "
          f"{len(notes)} notes, pool {POOL.stat().st_size / 1024:.0f}kb, "
          f"{len(out.splitlines())} lines")
    if misses:
        label = "read as plain callouts" if REVIEW else "matched no pattern"
        print(f"build_calc: {len(misses)} sentences {label}:", file=sys.stderr)
        for card, src, s in misses:
            print(f"  {card} [{src}] {s}", file=sys.stderr)


if __name__ == "__main__":
    main()
