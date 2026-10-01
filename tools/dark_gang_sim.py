#!/usr/bin/env python3
"""Pressure simulator for dark-gang.md list variants.

Plays your side card by card with a greedy policy against an opponent model
and counts how often the deck attacks. The numbers are relative: compare
variants against each other, never against real win rates.

    python3 tools/dark_gang_sim.py                          # the committed list
    python3 tools/dark_gang_sim.py --vs "Neo=NeoUpper:+1,Cape:-1"
    python3 tools/dark_gang_sim.py --vs "A=..." --vs "B=..." --n 6000 --opp gust,stall
    python3 tools/dark_gang_sim.py --cards                  # card keys for --vs

Opponent models:
  race   KOs your Active on most turns from their turn 2
  gust   alternates a Boss-KO on a benched engine piece with KOing the Active
  stall  alternates dragging up your highest-Retreat body with KOing the Active

Metrics, going first / going second:
  first<=3  your first real attack comes by your turn 3
  rearm     after they KO your Active, you attack on your next turn
  atk/8     real attacks in 8 turns (Chaotic Pain, Void Gale, Chain-Crazed)
  strand    turns a loaded attacker sat on the Bench with no way up
  dry       turns from turn 3 with nothing able to attack

Blind spots. The opponent KOs whatever it targets whatever its HP, so tanky
lines (a 350 HP Mega looping Void Gale, Hero's Cape) score worse than they
play. Boss's Orders, Risky Ruins, and the Cape do nothing here, so cutting
them looks free. BASE is dark-gang.md's list at commit df7ccfe; update it
when the list changes.
"""
import random, collections, sys

# ---------------------------------------------------------------- cards
POKE = {
    #  name        stage  hp   retreat ex    mega  dark  basicHP<=70
    'Okidogi':    (0, 250, 3, True,  False),
    'Gastly':     (0, 70,  1, False, False),
    'Haunter':    (1, 100, 1, False, False),
    'GengarEx':   (2, 280, 2, True,  False),
    'Mega':       (2, 350, 2, True,  True),
    'Toxel':      (0, 70,  1, False, False),
    'Toxtricity': (1, 140, 2, False, False),
    'Zorua':      (0, 70,  1, False, False),
    'Zoroark':    (1, 120, 1, False, False),
    'Pecharunt':  (0, 190, 1, True,  False),
    'Chansey':    (0, 120, 2, False, False),
    'Blissey':    (1, 300, 4, True,  False),
}
EVOLVES = {'Blissey': 'Chansey', 'Haunter': 'Gastly', 'Toxtricity': 'Toxel', 'Zoroark': 'Zorua',
           'GengarEx': 'Haunter', 'Mega': 'Haunter'}
STAGE2 = ('GengarEx', 'Mega')
SMALL_BASICS = ('Gastly', 'Toxel', 'Zorua')           # Poffin targets
NO_RULE_BOX = ('Gastly', 'Haunter', 'Toxel', 'Toxtricity', 'Zorua', 'Zoroark', 'Chansey')
NON_DARK = ('Chansey', 'Blissey')   # Surge, Janine's, Grimsley's, and Concealment skip them
SUPPORTERS = ('Lillie', 'Grimsley', 'Dawn', 'Hilda', 'Petrel', 'Janine', 'Boss',
              'AZ', 'Rosa', 'NsPlan')
ITEMS = ('Candy', 'Poffin', 'Pad', 'Switch', 'Recycler', 'EnergySwitch',
         'EnergySearch', 'Stretcher')


def is_poke(c): return c in POKE
def is_basic(c): return c in POKE and POKE[c][0] == 0


class Mon:
    __slots__ = ('name', 'e', 'neo', 'entered', 'poison', 'dmg')

    def __init__(s, name, t):
        s.name, s.e, s.neo, s.entered, s.poison, s.dmg = name, 0, False, t, False, 0

    @property
    def stage(s): return POKE[s.name][0]
    @property
    def ex(s): return POKE[s.name][3]
    @property
    def mega(s): return POKE[s.name][4]

    def D(s):  # Darkness provided
        return s.e + (2 if s.neo and s.stage == 2 else 0)

    def tot(s):
        return s.e + ((2 if s.stage == 2 else 1) if s.neo else 0)

    def __repr__(s): return f"{s.name}[{s.e}{'+N' if s.neo else ''}]"


# attack table: name -> (needD, needTotal, kind)   kind: real/weak
ATTACK = {
    'GengarEx': (2, 2, 'real'),
    'Mega': (2, 2, 'real'),
    'Okidogi': (2, 3, 'real'),
}


def can_attack(m):
    a = ATTACK.get(m.name)
    return a and m.D() >= a[0] and m.tot() >= a[1]


class Game:
    def __init__(s, deck, first, opp, rng, horizon=8, opp_from=2, log=False, force_prize=()):
        s.force_prize = list(force_prize)
        s.ko_pending = False
        s.rng = rng
        s.first, s.opp, s.horizon, s.opp_from = first, opp, horizon, opp_from
        s.log = log
        s.deck = list(deck)
        s.hand, s.discard, s.prizes = [], [], []
        s.active, s.bench = None, []
        s.t = 0
        s.opp_prizes = 0      # prizes opponent has taken
        s.my_prizes = 0       # prizes we have taken
        s.stats = collections.Counter()
        s.first_attack = None
        s.first_pain = None
        s.attacks_by = {}
        s.lost = False
        s.retreated = False
        s.attached = False
        s.sup_used = False
        s.chains_used = False

    # ------------------------------------------------------------ utils
    def L(s, *a):
        if s.log: print(f"  T{s.t}:", *a)

    def draw(s, n=1):
        for _ in range(n):
            if not s.deck:
                return False
            s.hand.append(s.deck.pop())
        return True

    def shuffle(s): s.rng.shuffle(s.deck)

    def inplay(s):
        return ([s.active] if s.active else []) + s.bench

    def count_line(s, names):
        return sum(1 for m in s.inplay() if m.name in names)

    def has_in_play(s, name): return any(m.name == name for m in s.inplay())

    def zoroarks_on_bench(s): return sum(1 for m in s.bench if m.name == 'Zoroark')

    def retreat_cost(s, m):
        return max(0, POKE[m.name][2] - 2 * s.zoroarks_on_bench())

    def take(s, card, src=None):
        src = s.hand if src is None else src
        src.remove(card)
        return card

    def search(s, pred):
        """Return first matching card name from deck (removed), shuffle."""
        for i, c in enumerate(s.deck):
            if pred(c):
                s.deck.pop(i)
                s.shuffle()
                return c
        s.shuffle()
        return None

    def bench_space(s): return 5 - len(s.bench)

    def put_bench(s, name):
        m = Mon(name, s.t)
        s.bench.append(m)
        return m

    def KO_mon(s, m):
        s.discard.append(m.name)
        # evolution cards underneath approximated: stage count of cards
        for _ in range(m.e): s.discard.append('D')
        if m.neo: s.discard.append('NeoUpper')

    def prize_value(s, m):
        v = 3 if m.mega else (2 if m.ex else 1)
        if s.has_in_play('Mega') and m.name not in NON_DARK:
            v -= 1
        return v

    # ---------------------------------------------------------- setup
    def setup(s):
        while True:
            s.shuffle()
            s.hand = [s.deck.pop() for _ in range(7)]
            if any(is_basic(c) for c in s.hand):
                break
            s.stats['mulligan'] += 1
            s.deck += s.hand
            s.hand = []
        order = ['Okidogi', 'Toxel', 'Gastly', 'Zorua', 'Pecharunt', 'Chansey']
        for n in order:
            if n in s.hand:
                s.take(n)
                s.active = Mon(n, 0)
                break
        s.bench_basics(setup=True)
        s.prizes = [s.deck.pop() for _ in range(6)]
        for fp in s.force_prize:
            if fp in s.prizes:
                continue
            src = s.deck if fp in s.deck else (s.hand if fp in s.hand else None)
            if src is None:
                continue
            src.remove(fp)
            swap = next((i for i, c in enumerate(s.prizes) if c not in s.force_prize), None)
            src.append(s.prizes[swap]); s.prizes[swap] = fp
            s.shuffle()

    def want_basic(s, n):
        return s.next_basic({n}) == n

    def _old_want_basic(s, n):
        line = {'Gastly': ('Gastly', 'Haunter', 'GengarEx', 'Mega'),
                'Toxel': ('Toxel', 'Toxtricity'),
                'Zorua': ('Zorua', 'Zoroark'),
                'Okidogi': ('Okidogi',),
                'Pecharunt': ('Pecharunt',)}[n]
        have = s.count_line(line)
        cap = {'Gastly': 3, 'Toxel': 2, 'Zorua': 1, 'Okidogi': 1, 'Pecharunt': 1}[n]
        if n == 'Gastly':
            # keep Gastly coming while Stage 2 cards remain to be built
            cap = 3 if s.count_line(('GengarEx', 'Mega')) < 2 else 2
        return have < cap

    BENCH_ORDER = [('Gastly', 1), ('Toxel', 1), ('Chansey', 1), ('Zorua', 1), ('Gastly', 2),
                   ('Toxel', 2), ('Gastly', 3), ('Pecharunt', 1), ('Okidogi', 1)]
    LINES = {'Chansey': ('Chansey', 'Blissey'), 'Gastly': ('Gastly', 'Haunter', 'GengarEx', 'Mega'),
             'Toxel': ('Toxel', 'Toxtricity'), 'Zorua': ('Zorua', 'Zoroark'),
             'Okidogi': ('Okidogi',), 'Pecharunt': ('Pecharunt',)}

    def next_basic(s, avail):
        """Which Basic the board wants next, from the names in avail."""
        for n, k in s.BENCH_ORDER:
            if n in avail and s.count_line(s.LINES[n]) < k:
                if n == 'Gastly' and k == 3 and s.count_line(('GengarEx', 'Mega')) >= 2:
                    continue
                return n
        return None

    def cff_pick(s, avail, got):
        """Call for Family's pick from the Basics in avail; got is how many it has benched."""
        if 'Okidogi' in avail and not s.has_in_play('Okidogi'):
            return 'Okidogi'
        return s.next_basic(avail)

    def bench_basics(s, setup=False):
        while s.bench_space() > 0:
            n = s.next_basic(set(c for c in s.hand if is_basic(c)))
            if not n:
                break
            s.take(n)
            s.put_bench(n)

    # --------------------------------------------------------- turn parts
    def items_search(s):
        progress = True
        while progress:
            progress = False
            if 'Poffin' in s.hand and s.bench_space() > 0 and any(
                    s.want_basic(b) and b in s.deck for b in SMALL_BASICS):
                s.take('Poffin'); s.discard.append('Poffin')
                got = 0
                for _ in range(2):
                    b = s.next_basic(set(c for c in s.deck if c in SMALL_BASICS))
                    if b and s.bench_space() > 0:
                        s.deck.remove(b); s.put_bench(b); got += 1
                s.shuffle()
                s.L('Poffin ->', got)
                progress = True
            if 'Pad' in s.hand:
                tgt = s.pad_target()
                if tgt:
                    s.take('Pad'); s.discard.append('Pad')
                    s.deck.remove(tgt); s.shuffle(); s.hand.append(tgt)
                    s.L('Pad ->', tgt)
                    s.bench_basics()
                    progress = True
            if 'EnergySearch' in s.hand and not s.energy_in_hand() and 'D' in s.deck:
                s.take('EnergySearch'); s.discard.append('EnergySearch')
                s.deck.remove('D'); s.shuffle(); s.hand.append('D')
                progress = True
            if 'Stretcher' in s.hand and not s.energy_in_hand() and 'D' in s.discard:
                s.take('Stretcher'); s.discard.append('Stretcher')
                s.discard.remove('D'); s.hand.append('D')
                progress = True
            if 'Recycler' in s.hand and s.discard.count('D') >= 3 and s.deck.count('D') <= 3:
                s.take('Recycler'); s.discard.append('Recycler')
                n = min(5, s.discard.count('D'))
                for _ in range(n): s.discard.remove('D'); s.deck.append('D')
                s.shuffle()
                progress = True

    def pad_target(s):
        want = []
        nb = s.next_basic(set(c for c in s.deck if c in SMALL_BASICS))
        if nb and s.bench_space() > 0 and s.count_line(s.LINES[nb]) == 0: want.append(nb)
        if s.want_basic('Gastly') and s.bench_space() > 0: want.append('Gastly')
        if s.has_in_play('Toxel') and not s.has_in_play('Toxtricity') and 'Toxtricity' not in s.hand:
            want.append('Toxtricity')
        if not s.count_line(('Chansey', 'Blissey')) and 'Chansey' not in s.hand and s.bench_space() > 0:
            want.append('Chansey')
        if s.has_in_play('Zorua') and not s.has_in_play('Zoroark') and 'Zoroark' not in s.hand:
            want.append('Zoroark')
        if s.want_basic('Toxel') and s.bench_space() > 0 and not s.count_line(('Toxel', 'Toxtricity')):
            want.append('Toxel')
        if s.want_basic('Zorua') and s.bench_space() > 0 and not s.count_line(('Zorua', 'Zoroark')):
            want.append('Zorua')
        # Haunter for a Gastly with no Candy route
        if any(m.name == 'Gastly' for m in s.inplay()) and 'Candy' not in s.hand and 'Haunter' not in s.hand:
            want.append('Haunter')
        for w in want:
            if w in s.deck:
                return w
        return None

    def evolve_all(s):
        if s.t < 2:
            return
        changed = True
        while changed:
            changed = False
            for m in s.inplay():
                if m.entered >= s.t:
                    continue
                # Stage 1s
                for s1, base in (('Toxtricity', 'Toxel'), ('Zoroark', 'Zorua'), ('Blissey', 'Chansey')):
                    if m.name == base and s1 in s.hand and not (
                            m is s.active and base == 'Toxel' and len(s.bench) <= 1):
                        s.take(s1); m.name = s1; m.entered = s.t; changed = True
                        s.L('evolve', s1)
                        break
                if m.entered >= s.t:
                    continue
                if m.name == 'Haunter':
                    s2 = s.pick_stage2()
                    if s2:
                        s.take(s2); m.name = s2; m.entered = s.t; changed = True
                        s.L('evolve Haunter ->', s2)
                        continue
                if m.name == 'Gastly':
                    s2 = s.pick_stage2()
                    if s2 and 'Candy' in s.hand:
                        s.take('Candy'); s.discard.append('Candy')
                        s.take(s2); m.name = s2; m.entered = s.t; changed = True
                        s.L('Candy ->', s2)
                        continue
                    if 'Haunter' in s.hand and not ('Candy' in s.hand and s2):
                        s.take('Haunter'); m.name = 'Haunter'; m.entered = s.t; changed = True
                        s.L('evolve Haunter')

    def pick_stage2(s):
        if 'GengarEx' in s.hand and not s.has_in_play('GengarEx'):
            return 'GengarEx'
        if 'Mega' in s.hand and not s.has_in_play('Mega'):
            return 'Mega'
        if 'GengarEx' in s.hand:
            return 'GengarEx'
        return None

    def energy_in_hand(s):
        return 'D' in s.hand or 'NeoUpper' in s.hand

    # ------------------------------------------------------- planning
    def toxtricity_count(s):
        return sum(1 for m in s.inplay() if m.name == 'Toxtricity')

    def plan_attack(s, sup):
        """Find a way to attack this turn. sup is the Supporter we may spend
        (or None). Returns (score, plan dict) or None."""
        if 'Neo' == sup: return None
        best = None
        surges = min(s.toxtricity_count(), s.deck.count('D'))
        hand = s.hand
        manual_D = (not s.attached) and 'D' in hand
        manual_neo = (not s.attached) and 'NeoUpper' in hand
        eswitch = hand.count('EnergySwitch')
        happy = sum(1 for m in s.inplay() if m.name == 'Blissey') - s.happy_used
        for X in s.inplay():
            if X.name not in ATTACK:
                continue
            needD, needT, _ = ATTACK[X.name]
            benched = X is not s.active
            # switch options
            sw_opts = []
            if not benched:
                sw_opts.append(('none', 0))
            else:
                a = s.active
                rc = s.retreat_cost(a)
                if not s.retreated and a.tot() >= rc and rc == 0:
                    sw_opts.append(('retreat0', 0))
                if 'Switch' in hand:
                    sw_opts.append(('Switch', 2))
                if not s.retreated and rc > 0 and a.e >= rc:
                    sw_opts.append(('retreatpay', 3 + rc))
                if (s.has_in_play('Pecharunt') and not s.chains_used
                        and X.name != 'Pecharunt'):
                    sw_opts.append(('Chains', 1))
                if sup == 'AZ':
                    sw_opts.append(('AZ', 4))
                if sup == 'Petrel' and 'Switch' in s.deck:
                    sw_opts.append(('PetrelSwitch', 4))
            for sw, swcost in sw_opts:
                d, t = X.D(), X.tot()
                used = {'surge': 0, 'manual': None, 'janine': False, 'rosa': False,
                        'eswitch': 0, 'nsplan': 0, 'happy': 0}
                # surges only while benched
                if benched:
                    k = min(surges, max(needT - t, needD - d, 0))
                    used['surge'] = k; d += k; t += k
                # supporter energy
                if sup == 'Janine' and (d < needD or t < needT) and s.deck.count('D') > used['surge']:
                    used['janine'] = True; d += 1; t += 1
                if sup == 'Rosa' and X.stage == 2 and s.rosa_ok() and (d < needD or t < needT):
                    used['rosa'] = True; d += 2; t += 2
                if sup == 'NsPlan' and (d < needD or t < needT):
                    spare = sum(m.e for m in s.bench if m is not X)
                    k = min(2, spare, max(needT - t, needD - d))
                    used['nsplan'] = k; d += k; t += k
                # manual
                if (d < needD or t < needT):
                    if manual_neo and X.stage == 2:
                        used['manual'] = 'NeoUpper'; d += 2; t += 2
                    elif manual_D:
                        used['manual'] = 'D'; d += 1; t += 1
                # energy switch from other bodies
                if (d < needD or t < needT) and happy > 0:
                    donors = sum(m.e for m in s.inplay() if m is not X)
                    k = min(happy, donors, max(needT - t, needD - d))
                    used['happy'] = k; d += k; t += k
                if (d < needD or t < needT) and eswitch:
                    donors = sum(m.e for m in s.inplay() if m is not X and m is not s.active) + \
                        (s.active.e if (s.active is not X and not benched) else 0)
                    k = min(eswitch, donors, max(needT - t, needD - d))
                    used['eswitch'] = k; d += k; t += k
                if d < needD or t < needT:
                    continue
                # poison for dog
                pois = False
                if X.name == 'Okidogi':
                    pois = (X.poison and not benched) or sw == 'Chains' or \
                        (used['janine'])
                # score: lower is better
                kind_pen = {'GengarEx': 0, 'Okidogi': 0 if pois else 3, 'Mega': 1}[X.name]
                score = kind_pen + swcost + (5 if sup else 0) + 2 * used['eswitch'] \
                    + used['surge'] * 0.1
                plan = dict(X=X, sw=sw, sup=sup, **used)
                if best is None or score < best[0]:
                    best = (score, plan)
        return best

    def rosa_ok(s):
        return (6 - s.my_prizes) > (6 - s.opp_prizes) and s.discard.count('D') >= 2

    def exec_plan(s, p):
        X = p['X']
        s.L('PLAN', X, p['sw'], p['sup'], 'surge', p['surge'], 'man', p['manual'],
            'jan', p['janine'])
        if p['sup']:
            s.take(p['sup']); s.discard.append(p['sup']); s.sup_used = True
            s.stats['sup_' + p['sup']] += 1
        for _ in range(p['surge']):
            if 'D' in s.deck:
                s.deck.remove('D'); X.e += 1; X.dmg += 20
        if p['surge']:
            s.shuffle()
        s.surges_done = p['surge']
        # switch in
        sw = p['sw']
        if sw != 'none':
            old = s.active
            if sw == 'retreat0':
                s.retreated = True
            elif sw == 'retreatpay':
                rc = s.retreat_cost(old)
                old.e -= rc
                s.discard += ['D'] * rc
                s.stats['retreat_energy'] += rc
                s.retreated = True
            elif sw == 'Switch':
                s.take('Switch'); s.discard.append('Switch')
            elif sw == 'PetrelSwitch':
                s.deck.remove('Switch'); s.shuffle(); s.discard.append('Switch')
            elif sw == 'Chains':
                s.chains_used = True
            s.stats['sw_' + sw] += 1
            old.poison = False
            s.bench.remove(X)
            s.bench.append(old)
            s.active = X
            if sw == 'Chains':
                X.poison = True
        if p['janine']:
            if 'D' in s.deck:
                s.deck.remove('D'); X.e += 1
                if X is s.active: X.poison = True
            # second Janine's energy to a benched attacker
            tgt = s.best_bench_target()
            if tgt and 'D' in s.deck:
                s.deck.remove('D'); tgt.e += 1
            s.shuffle()
        if p['rosa']:
            for _ in range(2):
                s.discard.remove('D'); X.e += 1
        if p['nsplan']:
            k = p['nsplan']
            for m in sorted(s.bench, key=lambda m: -m.e):
                while k and m.e:
                    m.e -= 1; X.e += 1; k -= 1
        if p['manual'] == 'D':
            s.take('D'); X.e += 1; s.attached = True
        elif p['manual'] == 'NeoUpper':
            s.take('NeoUpper'); X.neo = True; s.attached = True
        for _ in range(p.get('happy', 0)):
            donors = [m for m in s.inplay() if m is not X and m.e > 0]
            donors.sort(key=lambda m: (m.name in ATTACK, m.e))
            if donors:
                donors[0].e -= 1; X.e += 1; s.happy_used += 1
                s.stats['happy_switch'] += 1
        for _ in range(p['eswitch']):
            donors = [m for m in s.inplay() if m is not X and m.e > 0]
            donors.sort(key=lambda m: (m.name in ATTACK, m.e))
            if donors:
                s.take('EnergySwitch'); s.discard.append('EnergySwitch')
                donors[0].e -= 1; X.e += 1
        return X

    def best_bench_target(s, exclude=None):
        """Benched body that most wants Energy (next attacker)."""
        cands = [m for m in s.bench if m is not exclude and m.name not in NON_DARK]
        if not cands:
            return None

        def key(m):
            if m.name in ATTACK:
                short = max(0, ATTACK[m.name][1] - m.tot())
                if short > 0:
                    return (0, {'GengarEx': 0, 'Mega': 1, 'Okidogi': 2}[m.name], -m.e)
                return (4, 0, 0)
            if m.name == 'Haunter':
                return (1, 0, -m.e)
            if m.name == 'Gastly':
                return (2, 0, m.e)
            if m.name == 'Toxtricity':
                return (3, m.e, 0)
            return (9, 0, 0)
        cands.sort(key=key)
        c = cands[0]
        return c if key(c)[0] < 9 else None

    def setup_supporter(s, allow_lillie=True):
        """Play a setup Supporter. Returns True if one was played."""
        h = s.hand
        gastly_ready = [m for m in s.inplay() if m.name == 'Gastly' and m.entered < s.t]
        haunter_ready = [m for m in s.inplay() if m.name == 'Haunter' and m.entered < s.t]
        s2_hand = any(c in h for c in STAGE2)
        attackers = [m for m in s.inplay() if m.name in ATTACK]
        toxel_ready = [m for m in s.inplay() if m.name == 'Toxel' and m.entered < s.t]
        tox_line = s.count_line(('Toxtricity',)) + h.count('Toxtricity')

        # Grimsley's: from turn 2, when several targets remain
        if 'Grimsley' in h and s.t >= 2 and s.bench_space() > 0:
            targets = s.grimsley_targets()
            if sum(s.deck.count(n) for n in targets) >= 4 and (not attackers or tox_line == 0 or len(s.deck) < 40):
                return s.play_grimsley()
        if 'Hilda' in h:
            want = None
            if (gastly_ready or haunter_ready) and not s2_hand and ('Candy' in h or haunter_ready):
                want = 'GengarEx' if not s.has_in_play('GengarEx') else 'Mega'
            elif toxel_ready and tox_line == 0:
                want = 'Toxtricity'
            elif any(m.name == 'Chansey' and m.entered < s.t for m in s.inplay()) and \
                    not s.has_in_play('Blissey') and 'Blissey' not in h:
                want = 'Blissey'
            elif any(m.name == 'Zorua' and m.entered < s.t for m in s.inplay()) and \
                    not s.has_in_play('Zoroark') and 'Zoroark' not in h:
                want = 'Zoroark'
            elif not s.energy_in_hand() and attackers:
                want = 'GengarEx'
            if want:
                return s.play_hilda(want)
        if 'Dawn' in h and (not s2_hand or tox_line == 0):
            return s.play_dawn()
        if 'Petrel' in h and gastly_ready and s2_hand and 'Candy' not in h and 'Candy' in s.deck:
            s.take('Petrel'); s.discard.append('Petrel'); s.sup_used = True
            s.deck.remove('Candy'); s.shuffle(); s.hand.append('Candy')
            s.stats['sup_Petrel'] += 1
            return True
        if 'Grimsley' in h and s.t >= 2 and s.bench_space() > 0:
            return s.play_grimsley()
        if 'Hilda' in h:
            return s.play_hilda('GengarEx' if not s.has_in_play('GengarEx') else 'Mega')
        if 'Dawn' in h:
            return s.play_dawn()
        live = (s2_hand and (gastly_ready or haunter_ready) and ('Candy' in h or haunter_ready))
        if allow_lillie and 'Lillie' in h and (not live or len(h) <= 3):
            s.take('Lillie'); s.discard.append('Lillie'); s.sup_used = True
            s.deck += s.hand; s.hand = []; s.shuffle()
            s.draw(8 if s.my_prizes == 0 else 6)
            s.stats['sup_Lillie'] += 1
            s.L('Lillie')
            return True
        if 'Janine' in h and (s.active.name == 'Okidogi' or s.best_bench_target()):
            # Energy even without an attack this turn
            s.take('Janine'); s.discard.append('Janine'); s.sup_used = True
            s.stats['sup_Janine_build'] += 1
            tg = []
            if s.active.name == 'Okidogi' and s.active.e >= 1:
                tg.append(s.active)
            b = s.best_bench_target()
            if b: tg.append(b)
            b2 = s.best_bench_target(exclude=b)
            if b2 and len(tg) < 2: tg.append(b2)
            for m in tg[:2]:
                if 'D' in s.deck:
                    s.deck.remove('D'); m.e += 1
                    if m is s.active: m.poison = True
            s.shuffle()
            return True
        if 'Petrel' in h:
            want = None
            if gastly_ready and s2_hand and 'Candy' not in h: want = 'Candy'
            elif 'Pad' in s.deck: want = 'Pad'
            elif 'Candy' in s.deck: want = 'Candy'
            if want and want in s.deck:
                s.take('Petrel'); s.discard.append('Petrel'); s.sup_used = True
                s.deck.remove(want); s.shuffle(); s.hand.append(want)
                s.stats['sup_Petrel'] += 1
                return True
        return False

    def grimsley_targets(s):
        pri = []
        if not s.has_in_play('Toxtricity'): pri.append('Toxtricity')
        if not s.has_in_play('GengarEx'): pri.append('GengarEx')
        if 'Zoroark' in POKE and not s.has_in_play('Zoroark'): pri.append('Zoroark')
        if not s.has_in_play('Mega'): pri.append('Mega')
        if not s.has_in_play('Okidogi'): pri.append('Okidogi')
        if not s.has_in_play('Pecharunt'): pri.append('Pecharunt')
        pri += ['GengarEx', 'Haunter', 'Toxtricity', 'Gastly', 'Toxel']
        return pri

    def play_grimsley(s):
        s.take('Grimsley'); s.discard.append('Grimsley'); s.sup_used = True
        s.stats['sup_Grimsley'] += 1
        top = [s.deck.pop() for _ in range(min(7, len(s.deck)))]
        pick = None
        for n in s.grimsley_targets():
            if n in top:
                pick = n; break
        if pick:
            top.remove(pick)
            m = s.put_bench(pick)
            s.stats['grimsley_hit'] += 1
            s.L('Grimsley ->', pick)
        else:
            s.stats['grimsley_miss'] += 1
        s.deck = top + s.deck  # to bottom (deck pops from end = top)
        return True

    def play_hilda(s, want):
        s.take('Hilda'); s.discard.append('Hilda'); s.sup_used = True
        s.stats['sup_Hilda'] += 1
        order = [want, 'GengarEx', 'Mega', 'Toxtricity', 'Haunter', 'Zoroark', 'Blissey']
        for n in order:
            if n in s.deck:
                s.deck.remove(n); s.hand.append(n); break
        if 'NeoUpper' in s.deck and not s.energy_in_hand():
            s.deck.remove('NeoUpper'); s.hand.append('NeoUpper')
        elif 'D' in s.deck:
            s.deck.remove('D'); s.hand.append('D')
        s.shuffle()
        s.L('Hilda ->', want)
        return True

    def play_dawn(s):
        s.take('Dawn'); s.discard.append('Dawn'); s.sup_used = True
        s.stats['sup_Dawn'] += 1
        if not s.count_line(('Chansey', 'Blissey')) and 'Chansey' in s.deck and 'Blissey' in s.deck \
                and s.bench_space() > 0:
            s2 = 'GengarEx' if 'GengarEx' in s.deck else ('Mega' if 'Mega' in s.deck else None)
            for n in ('Chansey', 'Blissey', s2):
                if n:
                    s.deck.remove(n); s.hand.append(n)
            s.shuffle(); s.bench_basics()
            return True
        b = next((n for n in ['Gastly', 'Toxel', 'Okidogi', 'Zorua'] if n in s.deck and
                  (s.want_basic(n) or n == 'Gastly')), None)
        s1 = 'Toxtricity' if (s.count_line(('Toxel',)) and not s.has_in_play('Toxtricity')) else (
            'Zoroark' if (s.has_in_play('Zorua') and not s.has_in_play('Zoroark')) else (
                'Blissey' if (s.has_in_play('Chansey') and not s.has_in_play('Blissey')) else 'Haunter'))
        if s1 not in s.deck: s1 = next((n for n in ['Haunter', 'Toxtricity', 'Zoroark'] if n in s.deck), None)
        s2 = 'GengarEx' if 'GengarEx' in s.deck and not s.has_in_play('GengarEx') else ('Mega' if 'Mega' in s.deck else ('GengarEx' if 'GengarEx' in s.deck else None))
        for n in (b, s1, s2):
            if n:
                s.deck.remove(n); s.hand.append(n)
        s.shuffle()
        s.bench_basics()
        return True

    # --------------------------------------------------------- main turn
    def our_turn(s):
        s.t += 1
        s.retreated = s.attached = s.sup_used = s.chains_used = False
        s.happy_used = 0
        s.surged = False
        s.surges_done = 0
        if not s.draw():
            s.lost = True; s.stats['deckout'] += 1; return
        can_sup = not (s.first and s.t == 1)
        can_atk = not (s.first and s.t == 1)

        s.bench_basics()
        s.items_search()
        s.evolve_all()
        s.bench_basics()

        attacked = None
        if can_atk:
            p0 = s.plan_attack(None)
            if p0 is None and can_sup:
                # can a Supporter make an attack happen?
                best = None
                for sup in ('Janine', 'Rosa', 'AZ', 'NsPlan', 'Petrel'):
                    if sup in s.hand:
                        p = s.plan_attack(sup)
                        if p and (best is None or p[0] < best[0]):
                            best = p
                if best:
                    attacked = s.exec_plan(best[1])
                else:
                    # setup Supporter, then re-plan
                    if s.setup_supporter():
                        s.bench_basics(); s.items_search(); s.evolve_all(); s.bench_basics()
                    p1 = s.plan_attack(None)
                    if p1:
                        attacked = s.exec_plan(p1[1])
            elif p0 is not None:
                if can_sup:
                    # spend the Supporter on setup that keeps the plan intact
                    hand_before = list(s.hand)
                    s.setup_supporter(allow_lillie=False)
                    s.bench_basics(); s.items_search(); s.evolve_all(); s.bench_basics()
                p1 = s.plan_attack(None) or p0
                attacked = s.exec_plan(p1[1])
        elif can_sup:
            s.setup_supporter()
            s.bench_basics(); s.items_search(); s.evolve_all(); s.bench_basics()

        # leftover surges and attachment build the next attacker
        n_tox = s.toxtricity_count() - s.surges_done
        for _ in range(max(0, n_tox)):
            tgt = s.best_bench_target()
            if tgt and 'D' in s.deck:
                s.deck.remove('D'); tgt.e += 1; tgt.dmg += 20; s.shuffle()
                s.stats['surge_build'] += 1
        if not s.attached and 'D' in s.hand:
            tgt = None
            a = s.active
            if attacked is None and a.name == 'Okidogi' and a.e == 0:
                tgt = a
            elif attacked is None and a.name == 'Toxel' and a.e == 0 and can_atk and \
                    s.bench_space() > 0:
                tgt = a
            elif a.name in ATTACK and not can_attack(a):
                tgt = a
            else:
                tgt = s.best_bench_target() or (a if a.name in ATTACK else None)
            if tgt:
                s.take('D'); tgt.e += 1; s.attached = True
        # attack
        if attacked is not None and can_attack(s.active):
            X = s.active
            s.stats['atk_' + X.name] += 1
            s.my_prizes += 1
            if s.first_attack is None:
                s.first_attack = s.t
            if X.name == 'GengarEx' and s.first_pain is None:
                s.first_pain = s.t
            s.attacks_by[s.t] = 1
            if X.name == 'Mega':
                tgt = s.best_bench_target()
                if tgt and X.e > 0:
                    X.e -= 1; tgt.e += 1
        elif can_atk and s.active.name == 'Okidogi' and s.active.tot() >= 1:
            s.stats['musculature'] += 1
            for _ in range(2):
                if 'D' in s.deck: s.deck.remove('D'); s.active.e += 1
            s.active.poison = True
            s.shuffle()
        elif can_atk and s.active.name == 'Toxel' and s.active.tot() >= 1 and s.bench_space() > 0:
            s.stats['call_for_family'] += 1
            got = 0
            for _ in range(2):
                avail = set(c for c in s.deck if is_basic(c))
                n = s.cff_pick(avail, got)
                if n and s.bench_space() > 0:
                    s.deck.remove(n); s.put_bench(n); got += 1
            s.shuffle()
        else:
            # did we strand a ready attacker?
            if can_atk and any(can_attack(m) for m in s.bench):
                s.stats['stranded'] += 1
            elif can_atk and s.t >= 3:
                s.stats['dry'] += 1
        if s.ko_pending:
            s.stats['rearm_n'] += 1
            s.stats['rearm_hit'] += (s.t in s.attacks_by)
            s.ko_pending = False

    # ------------------------------------------------------- opponent
    def opp_turn(s, k):
        """k is the opponent's own turn number."""
        if k < s.opp_from:
            return
        pko = 0.4 if k == 2 else 0.85
        if s.rng.random() > pko:
            return
        mode = s.opp
        if mode == 'race':
            s.ko_active()
        elif mode == 'gust':
            # alternate: Boss-KO a benched engine piece, else KO Active
            if k % 2 == 0 and s.bench:
                s.boss_ko()
            else:
                s.ko_active()
        elif mode == 'stall':
            if k % 2 == 0 and s.bench:
                s.boss_stall()
            else:
                s.ko_active()

    def ko_active(s):
        s.ko_pending = True
        m = s.active
        s.opp_prizes += s.prize_value(m)
        s.KO_mon(m)
        s.active = None
        s.promote()

    def boss_ko(s):
        pri = {'Pecharunt': 0, 'Toxtricity': 1, 'Zoroark': 2, 'GengarEx': 3, 'Blissey': 4, 'Mega': 5}
        cands = sorted(s.bench, key=lambda m: (pri.get(m.name, 9), -m.e))
        m = cands[0]
        s.bench.remove(m)
        s.opp_prizes += s.prize_value(m)
        s.KO_mon(m)
        s.stats['bossed_' + m.name] += 1

    def boss_stall(s):
        # drag up the body that costs the most to leave, and leave it there
        cands = [m for m in s.bench if not can_attack(m)]
        if not cands:
            s.ko_active(); return
        cands.sort(key=lambda m: (-s.retreat_cost(m), m.e))
        m = cands[0]
        old = s.active
        old.poison = False
        s.bench.remove(m)
        s.bench.append(old)
        s.active = m
        s.stats['stalled'] += 1

    def promote(s):
        if not s.bench:
            s.lost = True
            s.stats['benched_out'] += 1
            return
        def key(m):
            if can_attack(m): return (0, 0)
            if m.name in ATTACK:
                short = ATTACK[m.name][1] - m.tot()
                return (1, short)
            keep = {'Zoroark': 3, 'Blissey': 3, 'Toxtricity': 2, 'Pecharunt': 1}.get(m.name, 0)
            return (2, keep, POKE[m.name][2])
        s.bench.sort(key=key)
        s.active = s.bench.pop(0)

    # ------------------------------------------------------------- game
    def play(s):
        s.setup()
        if not s.first:
            pass  # opponent's turn 1: no attack in the model
        for k in range(1, s.horizon + 1):
            s.our_turn()
            if s.lost: break
            if s.active.poison:
                s.active.dmg += 10
            opp_k = k if s.first else k + 1
            s.opp_turn(opp_k)
            if s.lost or s.opp_prizes >= 6:
                s.lost = True
                break
        return s


def build(d):
    deck = []
    for k, v in d.items():
        deck += [k] * v
    assert len(deck) == 60, (len(deck), d)
    return deck


BASE = {
    'Okidogi': 3, 'Gastly': 4, 'Haunter': 2, 'GengarEx': 3, 'Mega': 2, 'Toxel': 4, 'Toxtricity': 2,
    'Lillie': 3, 'Grimsley': 2, 'Dawn': 2, 'Hilda': 2, 'Petrel': 2, 'Janine': 1, 'Boss': 2, 'AZ': 1,
    'Candy': 4, 'Poffin': 2, 'Pad': 2, 'Switch': 2, 'Recycler': 2, 'Cape': 1, 'Ruins': 2,
    'D': 10,
}


def variant(**delta):
    d = dict(BASE)
    for k, v in delta.items():
        d[k] = d.get(k, 0) + v
        if d[k] == 0: del d[k]
    return d


def run(deck, n=20000, first=True, opp='race', seed=1, horizon=8, opp_from=2, force_prize=(), game=None):
    rng = random.Random(seed)
    agg = collections.Counter()
    fa = collections.Counter()
    atk_by = collections.Counter()
    tot_atk = 0
    lost = 0
    for i in range(n):
        g = (game or Game)(deck, first, opp, rng, horizon=horizon, opp_from=opp_from,
                           force_prize=force_prize).play()
        agg.update(g.stats)
        fa[g.first_attack] += 1
        tot_atk += len(g.attacks_by)
        for t in range(1, horizon + 1):
            atk_by[t] += (t in g.attacks_by)
        lost += g.lost
    out = {
        'first<=2': sum(v for k, v in fa.items() if k is not None and k <= 2) / n,
        'first<=3': sum(v for k, v in fa.items() if k is not None and k <= 3) / n,
        'attacks/6': sum(atk_by[t] for t in range(1, 7)) / n,
        'atk_rate_t3-6': sum(atk_by[t] for t in range(3, 7)) / (4 * n),
        'stranded/game': agg['stranded'] / n,
        'retreatE/game': agg['retreat_energy'] / n,
        'lost': lost / n,
        'dry/game': agg['dry'] / n,
        'rearm': agg['rearm_hit'] / max(1, agg['rearm_n']),
        'atk/8': sum(atk_by[t] for t in range(1, horizon + 1)) / n,
        'stats': agg,
    }
    return out


EXTRA_CARDS = ['NeoUpper', 'EnergySwitch', 'Rosa', 'NsPlan', 'EnergySearch', 'Stretcher',
               'Pecharunt', 'Zorua', 'Zoroark', 'Chansey', 'Blissey']


def parse_vs(spec):
    """'Label=Card:+1,Card:-1' -> (label, variant list)."""
    label, _, body = spec.partition('=')
    delta = {}
    for part in filter(None, (p.strip() for p in body.split(','))):
        card, _, k = part.partition(':')
        if card not in BASE and card not in EXTRA_CARDS:
            sys.exit(f"unknown card key {card!r}; run with --cards")
        delta[card] = delta.get(card, 0) + int(k)
    return label.strip() or body, variant(**delta)


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--vs', action='append', default=[], help="'Label=Card:+1,Card:-1', repeatable")
    p.add_argument('--n', type=int, default=4000, help='games per side (default 4000)')
    p.add_argument('--opp', default='gust,stall', help='opponent models, comma-separated')
    p.add_argument('--seed', type=int, default=35)
    p.add_argument('--cards', action='store_true', help='list the card keys and exit')
    a = p.parse_args()
    if a.cards:
        print('committed list:', ', '.join(f"{k} {v}" for k, v in BASE.items()))
        print('also modeled:  ', ', '.join(EXTRA_CARDS))
        return
    rows = [('committed list', dict(BASE))] + [parse_vs(v) for v in a.vs]
    for opp in a.opp.split(','):
        print(f"\n### opponent: {opp}, {a.n} games per side")
        print(f"{'variant':34s} | {'first<=3':>11s} | {'rearm':>11s} | {'atk/8':>9s} | {'strand':>9s} | {'dry':>9s}")
        for name, d in rows:
            deck = build(d)
            rF = run(deck, n=a.n, first=True, opp=opp, seed=a.seed)
            rS = run(deck, n=a.n, first=False, opp=opp, seed=a.seed + 1)
            f = lambda k: f"{rF[k] * 100:4.1f}/{rS[k] * 100:4.1f}"
            g = lambda k: f"{rF[k]:.2f}/{rS[k]:.2f}"
            print(f"{name:34s} | {f('first<=3'):>11s} | {f('rearm'):>11s} | {g('atk/8'):>9s} | "
                  f"{g('stranded/game'):>9s} | {g('dry/game'):>9s}")


if __name__ == '__main__':
    main()
